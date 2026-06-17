"""
aut2ltl.heur — pattern-matching heuristic approaches.

A theme folder dedicated to pattern-matching heuristics: one self-contained
subpackage per heuristic that recognises a specific automaton shape and acts on it.
Each is an independent peer with its own `algorithm.md`; nothing here is shared by
force — the grouping is by theme, not by a common base.

Unlike the engines (`aut2ltl.bls`) and the `decomp` approaches, a member here is NOT
necessarily a `Translator`: it may be an automaton rewriting or a fragment guess,
is typically **potentially unsound and gated by a Spot equivalence test**, and is
considered **WIP / immature**. This `__init__` imports none of them, so pulling in
one heuristic drags in neither its siblings nor their dependencies.

- `heur.fuse2` — `fuse2`: a gated TGBA→TGBA rewrite that unfolds a size-2
  non-accepting SCC into self-loops, extending `daisy`'s reach.

Import the heuristic you want directly, e.g. `from aut2ltl.heur.fuse2 import fuse2`.
"""
