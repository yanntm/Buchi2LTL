"""cake recipe — the liberal `best_of` over the default plus more ingredients.

Start from the shipped default (`best_daisy2`) as the trusted incumbent, then throw
the ingredients it leaves on the table as `best_of` ALTERNATIVES: the invariant strip
(`Invariant`, via `best_inv_all`), and a **deep** variant that piles decomposition
*below* the daisy peel — where the default only re-peels, `deep` makes daisy delegate
its residuals back to a `Strength ∘ Acc ∘ Scc` stack (finally wiring `SccDecompose`)
before the bls floor. `best_of` runs them all and keeps the smallest form per input,
but only displaces the trusted default on a SIGNIFICANT win (`significantly_smaller`),
so being liberal is pure upside, not risk: the aggressive variants win where they
help, the safe form stands everywhere else. (Many `best`-named siblings already exist;
`cake` is deliberately a fresh name — curate the set later.)
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.best_of import best_of, significantly_smaller
from aut2ltl.decomp.acceptance import AccDecompose
from aut2ltl.decomp.strength import StrengthDecompose
from aut2ltl.decomp.scc import SccDecompose
from aut2ltl.simplify_ltl import Simplify
from aut2ltl.compose import compose
from ..builder import daisy_pair, core
from .best_daisy2 import best_daisy2
from .best_inv_all import best_inv_all


def cake(options: Optional[Options] = None) -> Translator:
    """`best_of` over the default and more ingredients (see module docstring): the
    trusted `best_daisy2` incumbent, the inv-everywhere `best_inv_all`, and a `deep`
    variant whose daisy peel floors on a `Strength ∘ Acc ∘ Scc` stack (decomposition
    BELOW daisy, not just above) — a challenger displaces the incumbent only on a
    significant form win."""
    # Decomp above daisy AND below it: the peel delegates its residuals to a fresh
    # strength/acceptance/scc decomposition before hitting the bls core, instead of
    # the bare core. compose(...)(core) reads outermost-first.
    deep = Simplify(
        compose(StrengthDecompose, AccDecompose, daisy_pair,
                StrengthDecompose, AccDecompose, SccDecompose)(core(options)),
        "hi")
    return best_of(
        [best_daisy2(options), best_inv_all(options), deep],
        name="cake",
        beats=significantly_smaller(rel=0.25, floor=2),
    )


__all__ = ["cake"]
