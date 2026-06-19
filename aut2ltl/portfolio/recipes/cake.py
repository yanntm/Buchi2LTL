"""cake recipe — a small, shy `best_of`: the default vs one CHEAP rich variant.

Lessons from the first cakes, both confirmed on the benchmark:
  * more is not better — three assemblies (default + inv-everywhere + a deep
    below-daisy decomposition) bought only `inv` wins; the deep variant and a
    standalone `SccDecompose` won nothing on either corpus.
  * be shy with `best_of` — it must NOT hide two cascades. `best_of` runs *every*
    stage, so two full assemblies each flooring on `core = partscc ⊕ bls` run the
    expensive `bls` cascade TWICE per case (the ≈1.8× cost and the kinská counting
    timeout). And it is unnecessary: every inv win observed was `daisy+inv` or
    `inv+partscc` — none needed `bls`.

So cake is `best_of` over two stages, and only ONE of them carries a cascade:
  * `best_daisy2`, the trusted incumbent (full `core`, the one cascade). Run first,
    its `NOT_LTL` verdict short-circuits `best_of` — the rich variant is then skipped.
  * one RICH but CHEAP variant that weaves a little of every technique and floors on
    `partscc` ONLY (no `bls`): `Invariant` (inv, the proven lever) at the top and
    pre-`Acc`, `StrengthDecompose` (∨ strengths), `SccDecompose` (∨ accepting SCCs,
    woven in cheaply rather than as its own assembly), `AccDecompose` (∧ conjuncts),
    and `daisy_pair_inv` (the daisy/daisy2 peel with inv per descent). Where `partscc`
    cannot label a leaf the rich variant simply DECLINES, and `best_of` falls back to
    the incumbent — so it adds no second cascade, just a cheap structural+inv attempt.

`best_of`'s significance margin keeps the trusted form unless the rich variant is
significantly smaller — liberality as pure upside, at ≈one cascade plus a cheap probe.
(Many `best`-named siblings exist; `cake` stays a fresh name — curate later.)
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
from ..builder import daisy_pair_inv
from .best_daisy2 import best_daisy2


def cake(options: Optional[Options] = None) -> Translator:
    """`best_of` over the trusted default and one cheap every-technique variant (see
    module docstring): the incumbent `best_daisy2` (the one cascade), and a `Invariant
    ∘ Strength ∘ Scc ∘ Invariant ∘ Acc ∘ daisy_pair_inv` chain flooring on `PartScc`
    ONLY — it declines (no second cascade) where partscc cannot label, and displaces
    the default only on a significant form win."""
    rich = Simplify(
        compose(Invariant, StrengthDecompose, SccDecompose,
                Invariant, AccDecompose, daisy_pair_inv)(PartScc()),
        "hi")
    return best_of(
        [best_daisy2(options), rich],
        name="cake",
        beats=significantly_smaller(rel=0.25, floor=2),
    )


__all__ = ["cake"]
