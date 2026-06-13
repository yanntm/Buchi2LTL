"""
acceptance_dispatch.py — direct hierarchy-class φ per Theorem 2 / construction
-ref §9.3, ORTHOGONAL to the Muller-DNF assembly (reachability.py untouched).

The Muller DNF (`reconstruct_ltl_paper_style`) is the general `Δ₂` form and the
explosive one: it enumerates good config-sets G and, per G, asserts the inf-set
is *exactly* G via ⋀_{C∈G}¬Fin(C) ∧ ⋀_{C∉G}Fin(C). For the simpler acceptance
classes Theorem 2 gives a direct φ that avoids both explosions.

First class implemented here: **Büchi** (recurrence, `Π₂`). For a deterministic
Büchi cascade, acceptance is "some accepting config is visited infinitely
often", so

    φ_Büchi := ⋁_{C ∈ accepting configs} ¬Fin(C)              (§9.3, Π₂)

— no `Fin(C∉G)` web and no good-set enumeration. Soundness: `¬Fin(C)` ≡
"C ∈ inf-set"; the i.o.-set of a run is strongly connected, so Büchi acceptance
`inf ∩ α ≠ ∅` ≡ `⋁_{C∈α} (C ∈ inf)` ≡ `⋁_{C∈α} ¬Fin(C)` (a transient accepting
C contributes `¬Fin(C) ≡ false`, harmless). Returns None when the cascade is
not Büchi so the caller falls back to the Muller path.

Probe/verify: kr/testing/probe_buchi_dispatch.py (equiv vs original AND vs the
Muller output, plus size A/B). Other classes (coBüchi/looping/weak) are TODO.
"""

from __future__ import annotations
from typing import Optional

import kr.reachability_operators as _ops
from kr.fin import fin_c
from kr.ltl_builders import _Or, _Not, _ff, _simp_f, _tree_size_f
from kr.cascade import Cascade


def is_buchi_cascade(casc: Cascade) -> bool:
    """True iff the cascade's normalized D carries a plain Büchi condition
    (`Inf(0)`), so the direct Büchi dispatch applies."""
    if casc.num_levels == 0 or casc.original_aut is None:
        return False
    try:
        return bool(casc.original_aut.acc().is_buchi())
    except Exception:
        return False


def _reset_ops(casc: Cascade) -> None:
    """Fresh-build reset of the operator counters/memos (mirrors
    reconstruct_ltl_paper_style) so a dispatch build is independent and its
    size counters are accurate."""
    _ops.PAPER_REACH_CALLS = 0
    _ops.PAPER_FIN_CALLS = 0
    _ops.PAPER_MAX_LTL_SIZE = 0
    if hasattr(_ops, "_reach_memo"):
        _ops._reach_memo.clear()
    _ops._clear_casc_registry()
    _ops._register_casc(casc)
    if hasattr(_ops, "_lru_reach_strong"):
        _ops._lru_reach_strong.cache_clear()
    if hasattr(_ops, "_helper_memo"):
        _ops._helper_memo.clear()


def reconstruct_buchi(casc: Cascade) -> Optional["spot.formula"]:
    """Direct Büchi φ = ⋁_{C ∈ accepting configs} ¬Fin(C), or None if the
    cascade is not Büchi. accepting_configs() gives the recurrent accepting
    configs (reachable, on accepting cycles) — the tight α (transient accepting
    configs would only add `false` disjuncts and cost a wasted fin_c)."""
    if not is_buchi_cascade(casc):
        return None
    _reset_ops(casc)
    acc_cfgs = sorted(casc.accepting_configs())
    if not acc_cfgs:
        return _ff()    # Büchi with no recurrent accepting config -> empty
    res = _simp_f(_Or(*[_Not(fin_c(c, casc)) for c in acc_cfgs]))
    _ops.PAPER_MAX_LTL_SIZE = _tree_size_f(res)
    return res


__all__ = ["is_buchi_cascade", "reconstruct_buchi"]
