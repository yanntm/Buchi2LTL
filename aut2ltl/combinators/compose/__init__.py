"""aut2ltl.combinators.compose — decorator composition (∘) and its unit `identity`.

`compose(f, g, h)(leaf) == f(g(h(leaf)))`, so a recipe reads top-down as the term it
denotes; `identity` is the neutral element. See algorithm.md.

Public entries: `compose`, `identity`.
"""
from __future__ import annotations

from .compose import compose, identity

__all__ = ["compose", "identity"]
