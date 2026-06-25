"""best_inv_loop recipe — `best_daisy2` with the invariant strip in the peel loop.

`G(Σ)` factored at EVERY descent level (`daisy_pair_inv`), not once at the top. Deep
sub-automata have tighter local invariants the global `Σ` washes out, so inv fires as
the peel descends.
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.decomp.acceptance import AccDecompose
from aut2ltl.decomp.strength import StrengthDecompose
from aut2ltl.simplify_ltl import Simplify
from aut2ltl.combinators.compose import compose
from ..builder import daisy_pair_inv, core


def best_inv_loop(options: Optional[Options] = None) -> Translator:
    """`best_daisy2` with the invariant strip woven into the peel loop
    (`daisy_pair_inv`): `G(Σ)` factored at EVERY descent level, not once at the top.
    Deep sub-automata have tighter local invariants the global `Σ` washes out, so
    inv fires as the peel descends. A/B against `best_daisy2` to measure the
    per-descent invariant's effect (incl. faster NOT_LTL verdicts on counting-style
    automata, by shrinking the monoid the LTL-definability gate tests)."""
    return Simplify(
        compose(StrengthDecompose, AccDecompose, daisy_pair_inv)(core(options)), "hi")


__all__ = ["best_inv_loop"]
