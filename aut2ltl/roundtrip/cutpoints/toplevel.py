"""aut2ltl/roundtrip/cutpoints/toplevel.py — the `toplevel` finder (see algorithm.md).

`toplevel(operator)` returns the root iff it carries `operator`, else declines. A
factory: it builds a `Finder` parameterized by the Spot operator kind (e.g.
`toplevel(spot.op_And)`, `toplevel(spot.op_Or)`).
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import spot
    from aut2ltl.roundtrip.finder import Finder


def toplevel(operator: "spot.op") -> "Finder":
    """Build a `Finder` returning the root when `op(φ) = operator`, else `None`."""
    def find(formula: "spot.formula") -> "Optional[spot.formula]":
        return formula if formula._is(operator) else None
    return find
