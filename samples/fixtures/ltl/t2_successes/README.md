# fixtures/ltl/t2_successes — terminal-SCC heuristic successes

A curated corpus of LTL formulas for which the **terminal-SCC heuristic (tN)**
activated and produced a language-equivalent result. tN — generalized from the
original size-2 "t2" rule — accepts any terminal SCC of size ≥ 2 whose per-state
incoming `L` labels are pairwise mutually exclusive and strictly tighter than
true; the technique string reports the size captured (`t2`, `t3`, `t4`, …, e.g.
`sl+t3`).

107 formulas, one per line in `t2_successes.ltl`.
