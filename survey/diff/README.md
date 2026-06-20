# survey/diff — directional language comparison

Language-diff tooling for debugging a reconstruction against its ground truth.
Where `spot.are_equivalent` gives a bare yes/no, this reports **which way**
containment fails and **why** — a concrete witness word for each gap.

Importable as a module path:

    from survey.diff import diff_report, to_aut
    print(diff_report(gt, produced, "GT", "produced"))

`diff_report(a, b, name_a, name_b)` checks, for two LTL formulas / automata:

- `A ⊆ B ?` (every word of A accepted by B) and `B ⊆ A ?`;
- for each failing direction, a witness lasso in the difference, via
  `spot.difference(X, Y).accepting_word()`.

`to_aut(x)` coerces a formula string / `spot.formula` / automaton to an automaton.

## CLI

Two LTL/PSL formulas:

    python3 -m survey.diff.ltl_diff "GFa" "!a R (a | (!a & XFa))"

An HOA automaton **file** vs an LTL formula (the `ltl_diff` CLI parses both args
as LTL, so a file path needs this wrapper):

    python3 -m survey.diff.diff_hoa model.hoa "<ltl-formula>"

Run from the repo root (so `import survey.diff` and `import aut2ltl` resolve).
