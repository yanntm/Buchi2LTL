# tests/

Engine probes and unit tests for aut2ltl. Everything runs from the repo root via
`python3 -m tests.probes.<…>` (editable layout — no `sys.path` bootstraps).

The corpora and the evaluation harness have moved out: datasets live under
`samples/`, the survey harness is the `survey` package, and committed reference
runs are in `results/`. What remains here is purely *tests of the engine*.

## Layout

- `probes/` — engine probes + fast unit tests, grouped by area (`bls/`, `daisy2/`,
  `daisychain/`, `partscc/`, `heur/`, `inv/`, `language/`, `sccdecomp/`, …) plus
  the unit tests (`test_language.py`, `test_options.py`, `test_ltl_metrics.py`,
  `test_combinators.py`, `test_build_portfolio.py`, `test_best_of.py`). See
  `probes/README.md`.
- `logs/` — scratch run output; **gitignored**, never committed.

## Gates (before committing engine changes)

    python3 -m tests.probes.bls.test_kr_r4_audit      # must report CLEAN
    python3 -m survey --folder samples/validation      # must end SUCCESS

## Ground rules

- Run from the project root; placed scripts only — no `/tmp`, no `python -c`
  one-liners (see `CLAUDE.md`).
- Diagnostics are self-bound (≤15s per example); a blown budget is a finding,
  not something to wait on. Redirect long output to `logs/`, never `/tmp`.
- When comparing languages, report containment direction + a witness word
  (`python3 -m survey.diff.ltl_diff`), not just equivalence.
