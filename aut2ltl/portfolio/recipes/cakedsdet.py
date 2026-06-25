"""cakedsdet recipe — `cakeds` with the deterministic read-off `DaisystarDet`.

Identical in shape to `cakeds`, but both peels are `daisy_trio_det` (daisy →
daisy2 → daisystardet → daisystar → core) instead of `daisy_trio`: a *rejecting*
SCC with a **deterministic L-partition** is labelled by the exact, fixpoint-free
anchored read-off (`DaisystarDet`, see `aut2ltl/daisystardet/algorithm.md`) — smaller
than, and gate-free in principle compared to, the flat `Daisystar` — and the flat
`Daisystar` stays as the fallback for a non-deterministic rejecting star, so
coverage is at least `cakeds`'s. An A/B for `cakeds` over `--use cakedsdet`,
measuring the size gain of the deterministic form and whether the non-deterministic
fallback ever fires.
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.combinators.best_of import best_of, significantly_smaller
from aut2ltl.partscc import PartScc
from aut2ltl.decomp.acceptance import AccDecompose
from aut2ltl.decomp.strength import StrengthDecompose
from aut2ltl.decomp.scc import SccDecompose
from aut2ltl.decomp.inv import Invariant
from aut2ltl.simplify_ltl import Simplify
from aut2ltl.combinators.compose import compose
from ..builder import daisy_trio_det, daisy_trio_det_inv, core


def cakedsdet(options: Optional[Options] = None) -> Translator:
    """`cakeds` with the `daisy_trio_det` peel in both stages (see module
    docstring): the incumbent `strength ∘ acceptance ∘ daisy_trio_det` over `core`,
    and the cheap `Invariant ∘ Strength ∘ Scc ∘ Invariant ∘ Acc ∘ daisy_trio_det_inv`
    rich variant flooring on `PartScc` only — displacing the incumbent only on a
    significant form win."""
    incumbent = Simplify(
        compose(StrengthDecompose, AccDecompose, daisy_trio_det)(core(options)), "hi")
    rich = Simplify(
        compose(Invariant, StrengthDecompose, SccDecompose,
                Invariant, AccDecompose, daisy_trio_det_inv)(PartScc()),
        "hi")
    return best_of(
        [incumbent, rich],
        name="cakedsdet",
        beats=significantly_smaller(rel=0.25, floor=2),
    )


__all__ = ["cakedsdet"]
