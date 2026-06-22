# fixtures/ltl/terminal_2scc — labeled terminal 2-SCC candidates

A curated corpus of LTL formulas for which, after initial-state rewiring, a
terminal 2-state SCC was found whose incoming-OR labels `L(A)`, `L(B)` are both
tighter than true and mutually exclusive. The emitted candidate is

    G( L(A) & X O(A)  |  L(B) & X O(B) )

100 formulas, one per line in `terminal_2scc.ltl`.
