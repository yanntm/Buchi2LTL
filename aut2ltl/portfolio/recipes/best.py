"""best recipe — the prior (daisy-only) shipped default.

`strength(acceptance(daisy(core)))`: split by strength, then by acceptance conjunct,
peel self-loop daisies on each atom, floor on `core` (partscc, else the bls cascade).
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.decomp.acceptance import AccDecompose
from aut2ltl.decomp.strength import StrengthDecompose
from aut2ltl.simplify_ltl import Simplify
from ..builder import daisy, core


def best(options: Optional[Options] = None) -> Translator:
    """The prior default assembly: `strength(acceptance(daisy(core)))`.

    Splits the language by strength (∨ of weak/terminal/strong), then each part by
    acceptance conjunct (∧, on the deterministic form), and on each atom peels
    self-loop daisies before handing the residual core to `core` (partscc, else the
    bls cascade). The modern re-expression of the historical `Decompose / SlDriven /
    Decompose` graph, with `daisy` in place of the sl envelope and `partscc` for `t2`.

    One `hi` simplification sits OUTSIDE the whole assembly (our DAG combinators are
    size-indifferent, so a single final pass suffices — it replaces the per-Translator
    `_simp_f` the old `Sl`/`SlDriven` ran on their own output)."""
    return Simplify(StrengthDecompose(AccDecompose(daisy(core(options)))), "hi")


__all__ = ["best"]
