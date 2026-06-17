"""
aut2ltl.decomp.strength — the strength-decomposition composite Translator.

`StrengthDecompose(leaf)` splits a language into its weak / terminal / strong
sub-automata (Spot's strength decomposition, Renault et al. TACAS'13), whose union
is the language — exact for any automaton, no determinism needed — labels each by
recursion on itself, and recombines with ∨, delegating a single-strength language to
`leaf`. Imports only spot, the contract floor, and the engine-agnostic
`own_simplify`.

Public entry: `StrengthDecompose`. See algorithm.md for the construction.
"""

from .strength import StrengthDecompose

__all__ = ["StrengthDecompose"]
