"""best_inv_all recipe — inv stripped at EVERY decomposition boundary (experiment).

A maximally inv-woven variant of `best_daisy2`: factor the local `G(Σ)` at the top,
again around `Acc` (so each strength-part is stripped *before* `Acc` determinizes —
the one lever the peel-level `best_inv_loop` cannot reach, since the peel runs after
`detGenericMinimal`), and at every peel descent (`daisy_pair_inv`). `Invariant` is
idempotent and near-free (a BDD restrict + one conjunction), so stacking is cheap; it
self-credits only where a split has tightened the local `Σ` below the usually-vacuous
global one. Sound at each boundary by inv's exact factorization
(`L = strip(L,Σ) ∩ L(GΣ)`). Experimental — A/B vs `best_daisy2` (default) for size.
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.decomp.acceptance import AccDecompose
from aut2ltl.decomp.strength import StrengthDecompose
from aut2ltl.decomp.inv import Invariant
from aut2ltl.simplify_ltl import Simplify
from ..builder import daisy_pair_inv, core


def best_inv_all(options: Optional[Options] = None) -> Translator:
    """`best_daisy2` with `Invariant` woven at every boundary: top, around `Acc`
    (pre-determinization strip per strength-part), and per peel descent
    (`daisy_pair_inv`). See module docstring for the rationale."""
    return Simplify(
        Invariant(
            StrengthDecompose(
                Invariant(
                    AccDecompose(daisy_pair_inv(core(options)))))),
        "hi")


__all__ = ["best_inv_all"]
