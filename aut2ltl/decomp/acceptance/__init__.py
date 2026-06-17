"""
aut2ltl.decomp.acceptance — the acceptance-conjunct decomposition composite Translator.

`AccDecompose(leaf)` splits a deterministic automaton by the top-level conjuncts of
its acceptance condition, whose per-conjunct languages intersect to the original
(`L(A) = ⋂ L(A[acc:=c_i])`, exact when deterministic), labels each by recursion on
itself, and recombines with ∧, delegating an atomic (non-conjunctive) acceptance to
`leaf`. It asks the Language for the deterministic form, so the precondition is met
by construction. Imports only spot, the contract floor, and the engine-agnostic
`own_simplify`.

Public entry: `AccDecompose`. See algorithm.md for the construction.
"""

from .acceptance import AccDecompose

__all__ = ["AccDecompose"]
