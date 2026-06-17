"""
kr/cobuchi.py — the coBüchi (persistence, Σ₂) CascadeTranslator member.

φ = ⋀_{C ∈ marked configs} Fin(C), the dual of `buchi`. Self-gating: declines
when the cascade is not coBüchi. The predicate tests the NATURAL automaton
recovered via `postprocess(.,"generic")` — `decompose_aut`'s parity step hides
natural `Fin(0)` as `Inf(0)|Fin(1)` (on which `is_co_buchi` is False), and
`postprocess(.,"coBuchi")` is unsound (a recurrence cascade like GFa would pass).
α is the cover-aware `cobuchi_finite_configs()` set; empty α means every run
accepts -> true.
"""

from __future__ import annotations

from aut2ltl.bls.operators.fin import fin_c
from aut2ltl.ltl.builders import _And, _tt, _simp_f
from aut2ltl.bls.cascade import Cascade, CascadeHolder
from aut2ltl.bls.cascade_translator import CascadeTranslator
from aut2ltl.result import LTLResult


def is_cobuchi_cascade(casc: Cascade) -> bool:
    """True iff the cascade's language is coBüchi-recognizable (persistence),
    tested on the natural acceptance recovered via `postprocess(.,"generic")`."""
    if casc.num_levels == 0 or casc.original_aut is None:
        return False
    try:
        import spot
        gen = spot.postprocess(casc.original_aut, "deterministic", "generic")
        return bool(gen.acc().is_co_buchi())
    except Exception:
        return False


class CoBuchi:
    """coBüchi (persistence, Σ₂) member: φ = ⋀_{C ∈ marked configs} Fin(C)."""

    name = "cobuchi"

    def __call__(self, casc: CascadeHolder) -> LTLResult:
        if not is_cobuchi_cascade(casc):
            return LTLResult.decline()
        fin_cfgs = sorted(casc.cobuchi_finite_configs())
        if not fin_cfgs:
            res = _tt()    # coBüchi with no marked config -> all runs accept
        else:
            res = _simp_f(_And(*[fin_c(c, casc) for c in fin_cfgs]))
        return LTLResult.success(res, self.name)


cobuchi: CascadeTranslator = CoBuchi()


__all__ = ["is_cobuchi_cascade", "CoBuchi", "cobuchi"]
