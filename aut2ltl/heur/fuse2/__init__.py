"""
aut2ltl.heur.fuse2 — the size-2 SCC over-approximation rewrite.

`fuse2(aut)` is a gated **TGBA→TGBA rewriting** (NOT a Translator — it produces no
LTL): it unfolds a single non-accepting two-state SCC into a self-loop-only automaton
that `daisy` can label, returning the rewrite only when a Spot equivalence test
confirms the language was preserved, else `None`. A potentially-unsound heuristic
made safe by that gate; WIP / immature. See `algorithm.md` for the construction.

Public entry: `fuse2`.
"""

from .fuse2 import fuse2

__all__ = ["fuse2"]
