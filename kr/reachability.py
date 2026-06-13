"""
reachability.py — High-level LTL reconstruction from cascades using the paper K operators.

The core inductive operators (5 reachability formulas + fin_c) live in
reachability_operators.py.

This module provides the entry `reconstruct_bls` — the construction of
Boker, Lehtinen & Sickert, "On the Translation of Automata to Linear Temporal
Logic" (FoSSaCS 2022) — which delegates to the paper-faithful assembly
(reconstruct_ltl_paper_style): use of reach + fin_c (Lemma 7) + lifted Muller DNF
over good recurrent config sets (from Spot scc_info). No pattern matching,
no inf-often guessing, no special shortcuts for 1L/init-acc/trapping.
"""

from __future__ import annotations
import os
from typing import Any, Dict, List, Optional, Tuple

import spot

# Re-export the core operators so existing callers (examples, tests) continue to work.
# All 1L special case code has been deleted; the implementation is the pure generalized
# inductive 5 formulas for all depths.
from .reachability_operators import (  # noqa: F401
    letters_to_prop,
    make_guard,
    simplify_ltl,
    normalize_ltl,
    reach_strong,
    reach_weak,
    PAPER_REACH_CALLS,
    PAPER_FIN_CALLS,
    PAPER_MAX_LTL_SIZE,
)
from .fin import fin_c  # noqa: F401
from .ltl_builders import (
    _And, _Or, _Not, _tt, _ff, _simp_f, _str_f, _short_f, _normalize_ltl,
    _tree_size_f,
)

from .cascade import Cascade

def _compute_good_muller_sets(casc: Cascade) -> list:
    """Compute the good Müller sets M on configs (w.r.t. our normalized D).

    We now prefer the proper computation on the pruned configuration automaton:
    reachable configs from init (BFS), build pruned config twa with lifted acc,
    scc_info on the *config graph*, non-rejecting SCCs give the recurrent config
    sets M that can occur i.o. on accepting paths from the initial config.
    This actually uses the config automaton and does the reachability pruning +
    enumeration of accepting recurrent components on the lifted structure
    (as per paper/algo2).

    Falls back to state-SCC mapping (pruned to reachable) if the config graph
    analysis is not available.
    """
    # Prefer the new config-graph based (pruned + actual use of config aut)
    if hasattr(casc, 'compute_good_muller_sets'):
        try:
            res = casc.compute_good_muller_sets()
            if res is not None:
                return res
        except Exception:
            pass
    # old fallback (with reachable prune)
    reach = set(casc.reachable_configs()) if hasattr(casc, 'reachable_configs') else set(casc.all_configs())
    if casc.original_aut is None:
        acc = casc.accepting_configs()
        acc = {c for c in acc if c in reach}
        return [frozenset([c]) for c in acc] if acc else []
    aut = casc.original_aut  # the normalized det D (our working automaton)
    try:
        si = spot.scc_info(aut)
    except Exception:
        # fallback
        acc = casc.accepting_configs()
        acc = {c for c in acc if c in reach}
        return [frozenset([c]) for c in acc] if acc else []
    good = []
    for scci in range(si.scc_count()):
        if not si.is_rejecting_scc(scci):
            states = [s for s in range(aut.num_states()) if si.scc_of(s) == scci]
            m = frozenset(casc.state_to_config.get(s) for s in states if s in casc.state_to_config and casc.state_to_config.get(s) in reach)
            if m:
                good.append(m)
    return good


def reconstruct_ltl_paper_style(casc: Cascade) -> "spot.formula":
    """Paper-faithful top-level assembly (steps 5-6 / Lemma 7 in algorithm.md).

    Uses the reachability operators (the 5 formulas) inside fin_c / Fin(C), then
    for the lifted Müller condition α' = good_Ms on configs (w.r.t. the normalized
    deterministic D stored in the Cascade):
        ϕ = ∨_M ( ∧_{C∈M} ¬Fin(C)  ∧  ∧_{C∉M} Fin(C) )
    This asserts that the exact set of configs visited i.o. is some good M from α'.

    Returns the hash-consed `spot.formula` DAG — the construction's native,
    compact form. Flattening it (str) unfolds the sharing and is the one
    operation whose cost tracks the paper's tree bound; callers that truly
    need text use `reconstruct_ltl_str` (or `str()` on a sub-term) knowingly,
    under their own budgets.

    good_Ms come from Spot's scc_info on non-rejecting SCCs of D (those with accepting
    cycles) -- enumerating the recurrent sets Spot exhibits on D, not blind powerset.
    Keeps #terms small.
    """
    # reset counters owned by reachability_operators
    import kr.reachability_operators as _ops
    _ops.PAPER_REACH_CALLS = 0
    _ops.PAPER_FIN_CALLS = 0
    _ops.PAPER_MAX_LTL_SIZE = 0
    if hasattr(_ops, "_reach_memo"):
        _ops._reach_memo.clear()
    _ops._clear_casc_registry()
    cid = _ops._register_casc(casc)
    # clear lru on R* for fresh construction (arch adoption)
    if hasattr(_ops, "_lru_reach_strong"):
        _ops._lru_reach_strong.cache_clear()
    if hasattr(_ops, "_helper_memo"):
        _ops._helper_memo.clear()

    if casc.num_levels == 0:
        # trivial (num_levels==0 is degenerate; normally we have the normalized D)
        if casc.original_aut is not None:
            aut = casc.original_aut  # the normalized det D
            acc_cond = str(aut.get_acceptance()).strip().lower()
            if acc_cond in ("t", "true", "1", "0 t"):
                return _tt()
            if acc_cond in ("f", "false", "0 f"):
                return _ff()
            has_acc = any(bool(list(e.acc.sets())) for s in range(aut.num_states()) for e in aut.out(s))
            return _tt() if has_acc else _ff()
        return _tt()

    good_ms = _compute_good_muller_sets(casc)
    if not good_ms:
        return _ff()

    trace_on = getattr(_ops, "TRACE_ON", False)
    all_c = set(casc.all_configs())
    if trace_on:
        print("[TRACE_ASSEMBLY] good_ms=", [set(m) for m in good_ms])
        print("[TRACE_ASSEMBLY] all_configs=", all_c)
    # Whole assembly on spot.formula objects (hash-consed DAG sharing): fin_c per
    # config computed ONCE, reused across Muller terms; stringify only at the end.
    fin_by_c = {c: fin_c(c, casc) for c in sorted(all_c)}
    fold_absorbing = os.environ.get("KR_FOLD_ABSORBING_M", "1") != "0"
    terms_f = []
    for Mf in good_ms:
        M = set(Mf)
        not_M = all_c - M
        # Absorbing-M fold: if M is a terminal SCC of the config graph, the
        # Fin(C∉M) conjuncts are implied by ⋀_{c∈M}¬Fin(C) and are dropped.
        drop_fin = fold_absorbing and casc.is_absorbing_config_set(M)
        if trace_on:
            print(f"[TRACE_ASSEMBLY] for M={M} not_M={not_M} "
                  f"absorbing={drop_fin}")
            for c in M:
                print(f"[TRACE_ASSEMBLY]   !fin({c}) = {_short_f(_Not(fin_by_c[c]), 200)}")
            if not drop_fin:
                for c in not_M:
                    print(f"[TRACE_ASSEMBLY]   fin({c}) = {_short_f(fin_by_c[c], 200)}")
        and_parts = [_Not(fin_by_c[c]) for c in M]
        if not drop_fin:
            and_parts += [fin_by_c[c] for c in not_M]
        term_f = _simp_f(_And(*and_parts))
        if trace_on:
            print(f"[TRACE_ASSEMBLY]   term for M = {_short_f(term_f, 200)}")
        terms_f.append(term_f)
    if not terms_f:
        return _ff()
    res_f = _simp_f(_Or(*terms_f))
    if trace_on:
        print("[TRACE_ASSEMBLY] final =", _short_f(res_f, 200))
    # Size metric is now the unfolded-tree node count (memoized O(DAG) walk),
    # not the flat string length — the DAG is never serialized here.
    _ops.PAPER_MAX_LTL_SIZE = _tree_size_f(res_f)
    return res_f


def reconstruct_ltl_str(casc: Cascade) -> str:
    """Historical flat-string entry point. Unfolds the shared DAG into text —
    O(tree), which on multi-level cases is the double-exp the DAG avoids.
    Kept only for callers that genuinely need LTL text (file export, external
    tools); everything in-process should consume the formula object."""
    return _str_f(reconstruct_ltl_paper_style(casc))


def reconstruct_bls(casc: Cascade) -> "spot.formula":
    """Reconstruct LTL from a Cascade via the BLS construction.

    BLS = Boker, Lehtinen & Sickert, "On the Translation of Automata to Linear
    Temporal Logic" (FoSSaCS 2022) — the systematic algebraic translation from a
    counter-free deterministic ω-automaton to LTL over the Krohn-Rhodes / holonomy
    reset cascade. Delegates to the paper-faithful implementation: the five
    inductive reachability formulas (via fin_c for Lemma 7) + assembly of the
    Muller DNF over good recurrent config sets (reconstruct_ltl_paper_style).
    No ad-hoc, no shape inspection, no inf-often approximations. Returns the
    hash-consed spot.formula (see reconstruct_ltl_paper_style).
    """
    # Depth guard dropped (was 3 levels during find-issues-small-first dev):
    # the ladder is green through 3L and the construction is fully memoized
    # with a distinct-subproblem guard (KR_REACH_GUARD), which is the real
    # runaway protection. KR_MAX_LEVELS gives an opt-in ceiling if ever needed.
    max_levels = int(os.environ.get("KR_MAX_LEVELS", "0"))
    if max_levels > 0 and casc.num_levels > max_levels:
        raise NotImplementedError(
            f"Reconstruction depth ceiling KR_MAX_LEVELS={max_levels} "
            f"(got {casc.num_levels} levels)."
        )
    return reconstruct_ltl_paper_style(casc)


# --- Acceptance-type dispatch (TODO P1: construction-ref §9.3) ---

def build_phi(casc: Cascade, acceptance_type: str = "muller", acceptance_data=None) -> "spot.formula":
    """Acceptance-type dispatch. Muller — the primary, validated path —
    delegates to reconstruct_ltl_paper_style (formula object out).

    The direct hierarchy-preserving forms (looping-Büchi/coBüchi Σ₁/Π₁,
    Büchi/coBüchi Π₂/Σ₂, weak Δ₁ end_in(G)) are TODO P1; the previous
    string-pasting sketches for them were dropped with the str() API
    (they were placeholders with `if ...` ellipsis conditions, never live).
    """
    if acceptance_type in ("muller", None):
        return reconstruct_ltl_paper_style(casc)
    raise NotImplementedError(
        f"build_phi acceptance_type={acceptance_type!r}: direct "
        f"hierarchy-class forms are TODO P1 (construction-ref §9.3); "
        f"use the Muller path.")


__all__ = [
    "reconstruct_bls",
    "reconstruct_ltl_paper_style",
    "reconstruct_ltl_str",
    "simplify_ltl",
    "normalize_ltl",
    "reach_strong",
    "reach_weak",
    "fin_c",
    "build_phi",
    # plus re-exports from operators (base cases + generalized)
]
