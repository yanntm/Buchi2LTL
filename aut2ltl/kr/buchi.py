"""
kr/buchi.py — the Büchi (recurrence, Π₂) CascadeTranslator member.

φ = ⋁_{C ∈ accepting configs} ¬Fin(C). Self-gating: declines when the cascade is
not Büchi. α is the cover-aware `buchi_accepting_configs()` reader — the lift
section would under-approximate on a holonomy cover — and a transient accepting
config only adds a ¬Fin≡false disjunct, so the looser cover set stays sound.
"""

from __future__ import annotations

import aut2ltl.kr.reachability_operators as _ops
from aut2ltl.kr.fin import fin_c
from aut2ltl.kr.ltl_builders import _Or, _Not, _ff, _simp_f, _tree_size_f
from aut2ltl.kr.cascade import Cascade
from aut2ltl.contract import LTLFormulaResult, CascadeTranslator


def is_buchi_cascade(casc: Cascade) -> bool:
    """True iff the cascade's normalized D carries a plain Büchi condition
    (`Inf(0)`), so the direct Büchi member applies."""
    if casc.num_levels == 0 or casc.original_aut is None:
        return False
    try:
        return bool(casc.original_aut.acc().is_buchi())
    except Exception:
        return False


class Buchi:
    """Büchi (recurrence, Π₂) member: φ = ⋁_{C ∈ accepting configs} ¬Fin(C)."""

    name = "buchi"

    def __call__(self, casc: Cascade) -> LTLFormulaResult:
        if not is_buchi_cascade(casc):
            return LTLFormulaResult.decline()
        _ops.reset_build_state(casc)
        acc_cfgs = sorted(casc.buchi_accepting_configs())
        if not acc_cfgs:
            res = _ff()    # Büchi with no recurrent accepting config -> empty
        else:
            res = _simp_f(_Or(*[_Not(fin_c(c, casc)) for c in acc_cfgs]))
        _ops.PAPER_MAX_LTL_SIZE = _tree_size_f(res)
        return LTLFormulaResult(formula=res, technique={self.name})


buchi: CascadeTranslator = Buchi()


__all__ = ["is_buchi_cascade", "Buchi", "buchi"]
