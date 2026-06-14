"""
kr/muller.py — the general Muller-DNF assembly (the BLS core / `bls` leaf).

This is the explosive but fully general Δ₂ form: for the lifted Müller condition
α' = good config-sets M (the recurrent sets the normalized D actually exhibits),

    φ = ⋁_M ( ⋀_{C∈M} ¬Fin(C)  ∧  ⋀_{C∉M} Fin(C) )

asserting the set of configs visited infinitely often is exactly some good M.
`reconstruct_muller` is the leaf the dispatch chain falls back to when no simpler
acceptance class applies; it always produces a formula (never declines). The five
inductive reachability formulas it relies on (via fin_c / Fin(C)) live in
reachability_operators.py + fin.py.
"""

from __future__ import annotations
import os

import spot

import aut2ltl.kr.reachability_operators as _ops
from .fin import fin_c
from .ltl_builders import _And, _Or, _Not, _tt, _ff, _simp_f, _short_f, _tree_size_f
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


def reconstruct_muller(casc: Cascade) -> "spot.formula":
    """Assemble the general Muller DNF over the good config-sets of `casc`.

    Returns the hash-consed spot.formula DAG (never serialized here). Trivial
    cascades collapse to ⊤/⊥; an empty good-set family is the empty language ⊥.
    """
    # reset counters owned by reachability_operators
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
    # Per-conjunct Fin fold (default on; KR_FOLD_FIN_REACH=0 restores the full
    # Muller term). For a good set M, keep Fin(C∉M) only for C reachable from M
    # in the config graph: a run with Inf⊇M (the ¬Fin(C∈M) conjuncts) has Inf
    # strongly connected, so any C∈Inf is reachable from M — hence C unreachable
    # from M is visited finitely and its Fin(C) is implied (config_graph
    # .configs_reachable_from). Subsumes the absorbing-M fold. We decide kept
    # configs BEFORE building fin_c — the explosive part of the construction —
    # so dropped configs cost nothing.
    fold_fin = os.environ.get("KR_FOLD_FIN_REACH", "1") != "0"
    specs = []          # (M, kept_not_M, not_M) per good set
    needed = set()      # configs whose fin_c we actually build
    for Mf in good_ms:
        M = set(Mf)
        not_M = all_c - M
        if fold_fin:
            reach_M = casc.configs_reachable_from(M)
            kept_not_M = {c for c in not_M if c in reach_M}
        else:
            kept_not_M = not_M
        specs.append((M, kept_not_M, not_M))
        needed |= M
        needed |= kept_not_M
    # fin_c per needed config computed ONCE (hash-consed, reused across terms).
    fin_by_c = {c: fin_c(c, casc) for c in sorted(needed)}
    terms_f = []
    for (M, kept_not_M, not_M) in specs:
        if trace_on:
            print(f"[TRACE_ASSEMBLY] for M={M} not_M={not_M} "
                  f"kept_fin={kept_not_M} dropped_fin={not_M - kept_not_M}")
            for c in M:
                print(f"[TRACE_ASSEMBLY]   !fin({c}) = {_short_f(_Not(fin_by_c[c]), 200)}")
            for c in kept_not_M:
                print(f"[TRACE_ASSEMBLY]   fin({c}) = {_short_f(fin_by_c[c], 200)}")
        and_parts = [_Not(fin_by_c[c]) for c in M] + [fin_by_c[c] for c in kept_not_M]
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


__all__ = ["reconstruct_muller", "_compute_good_muller_sets"]
