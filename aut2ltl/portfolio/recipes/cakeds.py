"""cakeds recipe — `cake` with `daisystar` layered into the peel.

Identical in shape to `cake` (a shy `best_of` over the trusted incumbent and one
cheap rich variant), but both peels are the **trio** `daisy → daisy2 → daisystar`
instead of the pair `daisy → daisy2`: the reachability star `daisystar` gets a
turn after the recurrence star `daisy2` and before the floor. So a *rejecting*
star SCC that exits to a sink (the `F(a & Xb)` family — pure `LEAVE`, the
reachability dual `daisy2` deliberately declines) is peeled here instead of
falling through to the bls cascade (a large blob).

  * incumbent: `strength ∘ acceptance` over `daisy_trio`, flooring on `core`
    (partscc, else the one bls cascade) — `best_daisy2` with the trio peel.
  * rich (cheap, no second cascade): `Invariant ∘ Strength ∘ Scc ∘ Invariant ∘ Acc
    ∘ daisy_trio_inv` flooring on `PartScc` ONLY; declines where partscc cannot
    label, so `best_of` falls back to the incumbent.

`best_of`'s significance margin keeps the trusted form unless the rich variant is
significantly smaller. A drop-in A/B for `cake` over `--use cakeds`.
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.best_of import best_of, significantly_smaller
from aut2ltl.partscc import PartScc
from aut2ltl.decomp.acceptance import AccDecompose
from aut2ltl.decomp.strength import StrengthDecompose
from aut2ltl.decomp.scc import SccDecompose
from aut2ltl.decomp.inv import Invariant
from aut2ltl.simplify_ltl import Simplify
from aut2ltl.compose import compose
from ..builder import daisy_trio, daisy_trio_inv, core


def cakeds(options: Optional[Options] = None) -> Translator:
    """`cake` with the `daisy → daisy2 → daisystar` trio peel in both stages (see
    module docstring): the incumbent `strength ∘ acceptance ∘ daisy_trio` over
    `core`, and the cheap `Invariant ∘ Strength ∘ Scc ∘ Invariant ∘ Acc ∘
    daisy_trio_inv` rich variant flooring on `PartScc` only — displacing the
    incumbent only on a significant form win."""
    incumbent = Simplify(
        compose(StrengthDecompose, AccDecompose, daisy_trio)(core(options)), "hi")
    rich = Simplify(
        compose(Invariant, StrengthDecompose, SccDecompose,
                Invariant, AccDecompose, daisy_trio_inv)(PartScc()),
        "hi")
    return best_of(
        [incumbent, rich],
        name="cakeds",
        beats=significantly_smaller(rel=0.25, floor=2),
    )


__all__ = ["cakeds"]
