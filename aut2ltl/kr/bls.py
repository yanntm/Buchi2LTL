"""
kr/bls.py — the general-case CascadeTranslator member.

`Bls` is the fallback member of the dispatch chain: the full Boker–Lehtinen–
Sickert construction (the general Δ₂ Muller DNF). It accepts every cascade an
LTL-expressible language produces — the chain reaches it only when no simpler
acceptance class (acc / buchi / cobuchi / weak) applies — and never declines in
practice (LTL input is counter-free).

The heavy assembly is support in kr/muller.py (`assemble_muller_dnf`); this
module only wraps it into a named CascadeTranslator member.
"""

from __future__ import annotations

from aut2ltl.contract import LTLFormulaResult, CascadeTranslator
from .cascade import Cascade
from .muller import assemble_muller_dnf


class Bls:
    """General-case CascadeTranslator: the full Muller-DNF construction."""

    name = "bls"

    def __call__(self, casc: Cascade) -> LTLFormulaResult:
        return LTLFormulaResult(formula=assemble_muller_dnf(casc), technique={self.name})


bls: CascadeTranslator = Bls()


__all__ = ["Bls", "bls"]
