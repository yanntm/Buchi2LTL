"""aut2ltl.combinators.decompose — the ∧/∨ combine (and/or) combinator brick.

`decompose(split, connective, tag)` is the decorator that splits a language by `split`,
labels each part with the child, and recombines the part-formulas under `connective`
(∧ or ∨); `combine` is the underlying fuse of part-`LTLResult`s. The concrete splits
(strength / acceptance / scc) live in `aut2ltl/decomp/` and feed this operator. See
algorithm.md.

Public entries: `decompose`, `combine`, `Connective`, `Split`.
"""
from __future__ import annotations

from .decompose import decompose, combine, Connective, Split

__all__ = ["decompose", "combine", "Connective", "Split"]
