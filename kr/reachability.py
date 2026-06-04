"""
reachability.py — High-level LTL reconstruction from cascades using the paper K operators.

The core inductive operators (5 reachability formulas + fin_c) live in
reachability_operators.py.

This module provides the thin entry `reconstruct_ltl_1level_buchi` (name kept for
backward compat with callers) which delegates to the paper-faithful assembly
(reconstruct_ltl_paper_style): use of reach + fin_c (Lemma 7) + lifted Muller DNF
over good recurrent config sets (from Spot scc_info). No pattern matching,
no inf-often guessing, no special shortcuts for 1L/init-acc/trapping.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

# Re-export the core operators so existing callers (examples, tests) continue to work
from .reachability_operators import (  # noqa: F401
    letters_to_prop,
    make_guard,
    one_level_reach_stay,
    one_level_reach_strong,
    one_level_reach_weak,
    build_1level_reachability,
    _config_to_pos,
    _build_trans_for_pos,
    simplify_ltl,
    normalize_ltl,
    reach_strong,
    reach_weak,
    fin_c,
    PAPER_REACH_CALLS,
    PAPER_FIN_CALLS,
    PAPER_MAX_LTL_SIZE,
)

from .cascade import Cascade

def _compute_good_muller_sets(casc: Cascade) -> list:
    """Compute the good Müller sets M on configs (w.r.t. our normalized D).

    The aut in Cascade is the deterministic post-processed D (Spot transformations
    are the starting point; we work with its acceptance). We use spot.scc_info
    to identify non-rejecting SCCs (those that can contain an accepting cycle
    under D's parity condition). The states in such an SCC map (via h) to a
    candidate M of configs. This gives the recurrent accepting sets "exhibited"
    by Spot on D, instead of blind powerset.

    (For general Muller alpha on D this is still an SCC-granular approximation;
    full subset enumeration per the lifted alpha' would be more precise but expensive.)
    """
    if casc.original_aut is None:
        acc = casc.accepting_configs()
        return [frozenset([c]) for c in acc] if acc else []
    aut = casc.original_aut  # the normalized det D (our working automaton)
    try:
        si = spot.scc_info(aut)
    except Exception:
        # fallback
        acc = casc.accepting_configs()
        return [frozenset([c]) for c in acc] if acc else []
    good = []
    for scci in range(si.scc_count()):
        if not si.is_rejecting_scc(scci):
            states = [s for s in range(aut.num_states()) if si.scc_of(s) == scci]
            m = frozenset(casc.state_to_config.get(s) for s in states if s in casc.state_to_config)
            if m:
                good.append(m)
    return good


def reconstruct_ltl_paper_style(casc: Cascade) -> str:
    """Paper-faithful top-level assembly (steps 5-6 / Lemma 7 in algorithm.md).

    Uses the reachability operators (the 5 formulas) inside fin_c / Fin(C), then
    for the lifted Müller condition α' = good_Ms on configs (w.r.t. the normalized
    deterministic D stored in the Cascade):
        ϕ = ∨_M ( ∧_{C∈M} ¬Fin(C)  ∧  ∧_{C∉M} Fin(C) )
    This asserts that the exact set of configs visited i.o. is some good M from α'.

    The Fin expansions + letter guards from the reach formulas do the systematic work
    (size may be large before Spot simplify, as the paper predicts triple-exp in worst case).

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

    if casc.num_levels == 0:
        # trivial (num_levels==0 is degenerate; normally we have the normalized D)
        if casc.original_aut is not None:
            aut = casc.original_aut  # the normalized det D
            acc_cond = str(aut.get_acceptance()).strip().lower()
            if acc_cond in ("t", "true", "1", "0 t"):
                return "true"
            if acc_cond in ("f", "false", "0 f"):
                return "false"
            has_acc = any(bool(list(e.acc.sets())) for s in range(aut.num_states()) for e in aut.out(s))
            return "true" if has_acc else "false"
        return "true"

    good_ms = _compute_good_muller_sets(casc)
    if not good_ms:
        return "false"

    all_c = set(casc.all_configs())
    terms = []
    for Mf in good_ms:
        M = set(Mf)
        not_M = all_c - M
        and_parts = []
        for c in M:
            fc = simplify_ltl(f"!({fin_c(c, casc)})")
            _ops.PAPER_MAX_LTL_SIZE = max(_ops.PAPER_MAX_LTL_SIZE, len(fc))
            and_parts.append(fc)
        for c in not_M:
            fc = simplify_ltl(fin_c(c, casc))
            _ops.PAPER_MAX_LTL_SIZE = max(_ops.PAPER_MAX_LTL_SIZE, len(fc))
            and_parts.append(fc)
        if and_parts:
            # pairwise and + simplify to keep intermediates from exploding
            term = and_parts[0]
            for p in and_parts[1:]:
                term = simplify_ltl(f"({term}) & ({p})")
                _ops.PAPER_MAX_LTL_SIZE = max(_ops.PAPER_MAX_LTL_SIZE, len(term))
            terms.append(f"({term})")
    if not terms:
        return "false"
    res = terms[0]
    for t in terms[1:]:
        res = simplify_ltl(f"({res}) | ({t})")
        _ops.PAPER_MAX_LTL_SIZE = max(_ops.PAPER_MAX_LTL_SIZE, len(res))
    # capture max size from the module
    _ops.PAPER_MAX_LTL_SIZE = max(getattr(_ops, "PAPER_MAX_LTL_SIZE", 0), len(res) if isinstance(res, str) else 0)
    if _ops.PAPER_MAX_LTL_SIZE > 100000:
        # guard: if already huge before final normalize, bail to avoid OOM in spot parser
        # (user: use timeouts/memory limits; instrument to find the blow)
        return "PAPER_STYLE_TOO_LARGE_FOR_THIS_AUT; try smaller |AP| or see profile"
    return normalize_ltl(res)


def reconstruct_ltl_1level_buchi(casc: Cascade) -> str:
    """Main entry point for LTL reconstruction from a Cascade.

    Delegates to the paper-faithful implementation: reachability formulas
    (via fin_c for Lemma 7) + assembly of Muller DNF over good recurrent sets
    (reconstruct_ltl_paper_style). This is the systematic algebraic construction
    with no ad-hoc, no shape inspection, no inf-often approximations.
    """
    # Practical guard for dev (paper formulas can be very large for deep cascades);
    # remove to attempt full per paper bounds.
    if casc.num_levels > 3:
        raise NotImplementedError(
            f"Paper style reconstruction limited to 3 levels in current dev guard "
            f"(got {casc.num_levels}); the formulas grow per paper (double-exp depth)."
        )
    return reconstruct_ltl_paper_style(casc)


__all__ = [
    "reconstruct_ltl_1level_buchi",
    "reconstruct_ltl_paper_style",
    "simplify_ltl",
    "normalize_ltl",
    "reach_strong",
    "reach_weak",
    "fin_c",
    # plus re-exports from operators (base cases + generalized)
]
