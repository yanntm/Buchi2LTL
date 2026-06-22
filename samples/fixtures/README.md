# fixtures — interesting formulas & automata from development

A small, hand-curated corpus collected while developing aut2ltl: cases used for
manual testing, debugging the heuristics, and regression. Two parallel sides:

- **`ltl/`** — one folder per source set, each a `README.md` + a `<set>.ltl`
  (one formula per line, `#` comments): `formulas` (hand-picked), `f2_successes`
  / `t2_successes` / `terminal_2scc` (heuristic-success corpora).
- **`hoa/`** — ω-automata in HOA format. Hand-written examples live loose under
  `hoa/various/`. The per-set folders (`hoa/<set>/`, mirroring `ltl/`) are
  **generated** later by running `ltl2tgba` over each `ltl/<set>/` list — one
  automaton per formula.

So `ltl/` and `hoa/` share the same substructure: an `ltl/<set>/` of X formulas
becomes an `hoa/<set>/` of X automata.
