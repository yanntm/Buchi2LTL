"""aut2ltl.combinators.first_success — the choice (⊕) combinator brick.

`first_success` is the chain-of-responsibility composite: try the stages in order,
take the first language-faithful result, else decline. See algorithm.md.

Public entry: `first_success`.
"""
from __future__ import annotations

from .first_success import first_success

__all__ = ["first_success"]
