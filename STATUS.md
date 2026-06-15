# aut2ltl — Project Status

Project-level snapshot. For the **engine** state read `aut2ltl/kr/STATUS.md`
(the FoSSaCS'22 cascade core); for construction history read `docs/HISTORY.md`.

## What works

The FoSSaCS'22 automaton→LTL construction is implemented end-to-end and
semantically validated. The portfolio front end (`reconstruct_decomposed`:
decompose/recombine + the sl heuristic gate over the integrated kr cascade)
sweeps the Manna–Pnueli class ladder — every probed case verifies equiv=True.
Engine internals and the current size profile live in `aut2ltl/kr/STATUS.md`.

## Front end (CLI)

`aut2ltl/__main__.py` (`python3 -m aut2ltl`, console script `aut2ltl`) is the
portfolio front end: an LTL formula or HOA file in, an equivalent LTL formula
out. `--use` cites the techniques that may participate (`acc weak buchi cobuchi
bls str sl` producers + `sl_driven decompose` wrappers; `str` is the integrated
default cascade); omit it for the best default. `-O key=value` overrides any
declared option (`--list-options`/`--list-techniques` to discover). The verbose
report (technique, DAG/temporals/tree sizes, build time) goes to stderr (`-q`
silences); `--dag` dumps the formula DAG as graphviz dot; DECLINE ⇒ exit 1.

## Testing

The front-end survey is the correctness gate — it reconstructs a corpus through
the CLI and verifies each result with a Spot oracle (a test-only check, never a
client cost):

- `tests/survey.py` — corpus survey; per-formula CSV + a compact summary ending
  in `SUCCESS`/`FAIL`. `FAIL` = a verified non-equivalent formula (a definite
  wrong answer); spot timeouts / size explosions / >32-acc-set walls are their
  own categories, NOT failures (a DAG we built that Spot cannot verify is not
  our fault). The corpus is `tests/survey_formulas.py`.
- `tests/survey_sweep.sh` — the same survey across every `--use` configuration,
  one log each + a cross-config SUMMARY. `tests/survey_diff.py` diffs two CSVs.
  The committed release baseline is `tests/logs/reference/`.
- `tests/kr/test_kr_r4_audit.py` — structural audit gate (must stay CLEAN).

## Layout

`aut2ltl/contract.py` (floor) + `aut2ltl/language.py` ← `aut2ltl/kr` (pure
cascade engine) + `aut2ltl/sl` (heuristic engine) ← `aut2ltl/portfolio`
(combinators) ← `aut2ltl/__main__`. Engine-agnostic helpers in `aut2ltl/ltl`.
Tests under `tests/` (`survey*`, `tests/kr`, `tests/sl`, `tests/fixtures`).
