"""aut2ltl/roundtrip/finder.py — the Finder contract (Φ in algorithm.md).

`Finder` is the behavioral contract `roundtrip`'s node finder must satisfy:
`Φ : Formula → (Node | ⊥)` — given a formula, return one of its nodes (the cut), or
`None` to decline. A node is a subformula occurrence, represented by the
`spot.formula` itself (so `φ↓n = n`). The sole obligation: a returned node IS a
subformula of the argument.

The floor; it names no implementor — the concrete strategies live in `cutpoints/`.
"""
from __future__ import annotations

from typing import Optional, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    import spot


class Finder(Protocol):
    """`Φ : Formula → (Node | ⊥)`: map a formula to one of its nodes, or `None`."""

    def __call__(self, formula: "spot.formula") -> "Optional[spot.formula]":
        ...
