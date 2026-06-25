"""
aut2ltl.combinators.recurse — the recursive-descent combinator brick.

`recurse(step)` is the least fixpoint of a Translator endofunctor: the translator
`leaf` with `leaf = step(leaf)`, where `step(child)` decomposes the input one
level and delegates strictly-smaller sub-problems to `child`. It is the
self-reference complement of `first_success` (choice) among the portfolio's
primitive bricks — the shape `daisy` / `daisy_pair` / the `decomp` composites all
share, factored out so there is ONE place to add `best_of`, memoization, or a
per-descent layer. Pure knot-tier: no base case, no behaviour of its own;
termination and the floor are `step`'s. See README.md.

Public entry: `recurse`.
"""

from .recurse import recurse

__all__ = ["recurse"]
