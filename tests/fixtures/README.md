# Samples

This folder contains interesting LTL formulas and automata (in HOA format) used during development of the aut2ltl prototype.

Useful for:
- Manual testing
- Debugging the fusion heuristic
- Regression testing

## Key files

- `motivating_example.hoa` — the first HOA the user provided (`(p U q) & GFr`)
- `second_example.hoa` — the second HOA (`G (p -> X p) & GF q`)
- `very_weak_w_until.hoa` — the `!p1 W p0` example (trivial acceptance)
- `formulas.py` — some interesting LTL formulas as Python strings
