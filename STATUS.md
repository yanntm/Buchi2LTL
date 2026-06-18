# aut2ltl — Project Status

Project-level snapshot. For the **engine** state read `aut2ltl/bls/STATUS.md`
(the FoSSaCS'22 cascade core); for construction history read `docs/HISTORY.md`.

## What works

The FoSSaCS'22 automaton→LTL construction is implemented end-to-end and
semantically validated. The portfolio front end is the **`best` recipe** (the
no-`--use` default since 2026-06-18): `Simplify(strength(acceptance(daisy(core))),
"hi")` with `core = first(partscc, bls)` — strength/acceptance decomposition over a
self-loop daisy peel flooring on the kr cascade. It sweeps the Manna–Pnueli class
ladder — every probed case verifies equiv=True — and replaces the legacy
`Decompose / SlDriven / Decompose` graph that the benchmark caught producing a
verified FALSE. Engine internals and the size profile live in `aut2ltl/bls/STATUS.md`.

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
- `tests/benchmark/` — the portfolio evaluation **bench** (size, not a gate):
  `default` vs `best` over `inputs/` (the survey corpus + W/U/R chains + 105
  Kinská HOA), reusing the survey engine; `bench_sweep.sh` + `survey_diff.py`.
  Reference runs committed under `tests/benchmark/logs/reference/`. The first
  full run flagged a legacy-`default` **FALSE** (non-equivalent answer) on a
  strong-until chain that `best` reconstructs correctly — concrete evidence for
  promoting `best` to the default and retiring the legacy path.

## Layout

`aut2ltl/contract.py` (floor) + `aut2ltl/language.py` ← `aut2ltl/bls` (pure
cascade engine) + `aut2ltl/sl` (heuristic engine) ← `aut2ltl/portfolio`
(combinators) ← `aut2ltl/__main__`. Engine-agnostic helpers in `aut2ltl/ltl`.
Tests under `tests/` (`survey*`, `tests/kr`, `tests/sl`, `tests/fixtures`,
`tests/benchmark`). `aut2ltl/ltl/simplify` carries its own `algorithm.md` spec.
