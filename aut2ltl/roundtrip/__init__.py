"""
aut2ltl.roundtrip — the `roundtrip` Rewriter and its `Finder` contract.

`roundtrip(R, Φ)` is a Rewriter (`LTLResult → LTLResult`): locate one node via the
finder `Φ`, re-present the subformula there with the Rewriter `R`, relink in place.
See algorithm.md; the finder strategies live in `cutpoints/`.

Public entries: `roundtrip`, `Finder`.
"""

from .finder import Finder
from .roundtrip import roundtrip

__all__ = ["roundtrip", "Finder"]
