"""best_daisy2 recipe — the shipped default (the no-`--use` translator).

`best` with `daisy2` slipped into the peel layer: `strength ∘ acceptance` over the
`daisy`/`daisy2` peel pair (`daisy_pair`) flooring on `core`.
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.decomp.acceptance import AccDecompose
from aut2ltl.decomp.strength import StrengthDecompose
from aut2ltl.simplify_ltl import Simplify
from aut2ltl.compose import compose
from ..builder import daisy_pair, core


def best_daisy2(options: Optional[Options] = None) -> Translator:
    """The shipped `best` assembly with `daisy2` slipped into the peel layer:
    `strength ∘ acceptance` decomposition over the `daisy`/`daisy2` peel pair
    (`daisy_pair`) flooring on `core` (partscc, else the bls cascade). Identical to
    `best` except the peel tries the length-1 star `daisy2` before falling to the
    core — so a star SCC `daisy` cannot peel is taken by `daisy2` instead of
    descending straight to the cascade. The single `hi` simplification stays
    outside the whole assembly, exactly as in `best`."""
    return Simplify(
        compose(StrengthDecompose, AccDecompose, daisy_pair)(core(options)), "hi")


__all__ = ["best_daisy2"]
