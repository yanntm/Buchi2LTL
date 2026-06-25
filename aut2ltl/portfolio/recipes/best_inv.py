"""best_inv recipe — `best_daisy2` with the invariant layer applied ONCE at the top.

Factor the global `G(Σ)` out front, then the `best_daisy2` assembly. The global `Σ`
is usually vacuous, so this is benchmark-neutral — see `best_inv_loop` for the
per-descent placement where the invariant actually fires.
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.decomp.acceptance import AccDecompose
from aut2ltl.decomp.strength import StrengthDecompose
from aut2ltl.decomp.inv import Invariant
from aut2ltl.simplify_ltl import Simplify
from aut2ltl.combinators.compose import compose
from ..builder import daisy_pair, core


def best_inv(options: Optional[Options] = None) -> Translator:
    """`best_daisy2` with the invariant layer applied ONCE at the top: factor the
    global safety invariant `G(Σ)` out front (`Invariant`), then strength ∘
    acceptance decomposition over the daisy/daisy2 peel pair flooring on `core`.
    Sound for the one application (`L(A) = L(strip(A,Σ)) ∩ L(GΣ)`). The global `Σ`
    is usually vacuous, so this is benchmark-neutral — see `best_inv_loop` for the
    per-descent placement where the invariant actually fires."""
    return Simplify(
        compose(Invariant, StrengthDecompose, AccDecompose, daisy_pair)(core(options)), "hi")


__all__ = ["best_inv"]
