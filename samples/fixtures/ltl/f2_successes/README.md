# fixtures/ltl/f2_successes — size-2 fusion successes

A curated corpus of LTL formulas for which the **size-2 fusion heuristic (f2)**
produced a language-equivalent automaton. f2 fuses a 2-state pattern (typically
an `F(a & X b)`-shaped reachability) into a single over-approximating candidate
that turns out exact on these inputs.

~100 formulas, one per line in `f2_successes.ltl`.
