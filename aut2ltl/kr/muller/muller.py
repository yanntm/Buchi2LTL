"""
kr/muller/muller.py — the general Muller-DNF member (the BLS general case).

The explosive but fully general Δ₂ form: for the lifted Müller condition
α' = good config-sets M (the recurrent sets the normalized D actually exhibits),

    φ = ⋁_M ( ⋀_{C∈M} ¬Fin(C)  ∧  ⋀_{C∉M} Fin(C) )

asserting the set of configs visited infinitely often is exactly some good M.
`assemble_muller_dnf` is the assembly (casc → formula); the `Muller`
CascadeTranslator member wraps it into the general-case leaf, which always produces a
formula. The five inductive reachability formulas it relies on (via fin_c / Fin(C))
live in reachability_operators.py + fin.py. See algorithm.md.
"""

from __future__ import annotations
import os

import aut2ltl.kr.reachability_operators as _ops
from aut2ltl.kr.fin import fin_c
from aut2ltl.ltl.builders import _And, _Or, _Not, _tt, _ff, _simp_f, _short_f
from aut2ltl.kr.cascade import CascadeHolder, good_muller_sets
from aut2ltl.kr.cascade_translator import CascadeTranslator
from aut2ltl.result import LTLResult


def assemble_muller_dnf(casc: CascadeHolder) -> "spot.formula":
    """Assemble the general Muller DNF over the good config-sets of `casc`.

    Returns the hash-consed spot.formula DAG (never serialized here). Trivial
    cascades collapse to ⊤/⊥; an empty good-set family is the empty language ⊥.
    A fresh CascadeHolder carries empty memos and zeroed counters, so no reset is
    needed here.
    """
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

    good_ms = good_muller_sets(casc)
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
    return res_f


class Muller:
    """General-case CascadeTranslator: the full Muller-DNF construction (the BLS
    fallback). Reached only when no simpler acceptance class applies; never declines
    in practice (LTL input is counter-free)."""

    name = "muller"

    def __call__(self, casc: CascadeHolder) -> LTLResult:
        return LTLResult.success(assemble_muller_dnf(casc), self.name)


muller: CascadeTranslator = Muller()


__all__ = ["assemble_muller_dnf", "Muller", "muller"]
