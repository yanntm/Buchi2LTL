"""aut2ltl/roundtrip/cutpoints/root.py — the `root` finder (see algorithm.md).

`root(φ) = φ`: the whole formula as the cut node, never declining. Cutting it
relabels the entire formula.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import spot


def root(formula: "spot.formula") -> "spot.formula":
    """`root(φ) = φ`: return the whole formula as the cut node; never declines."""
    return formula
