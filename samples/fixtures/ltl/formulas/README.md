# fixtures/ltl/formulas — hand-picked development formulas

A few interesting LTL formulas collected while developing aut2ltl — small,
hand-chosen cases, not a generated corpus. Three groups, kept as `#` section
comments in `formulas.ltl`:

- **basic** — early cases that reconstructed cleanly (`(p U q) & GF r`, `FG a`,
  `a U b`, …), including one that exercises downstream invariants + the
  terminal-SCC path + precise SCC attachment.
- **f2-required** — needs the size-2 fusion heuristic (`X(p1 | F(p1 & Xp1))`).
- **problematic** — very-weak / release shapes that were historically tricky
  (`!p1 W p0`, `G!p2 R p1`).

The larger generated corpora live in the sibling sets
[`f2_successes`](../f2_successes), [`t2_successes`](../t2_successes) and
[`terminal_2scc`](../terminal_2scc).
