# aut2ltl — Project Status

Project-level snapshot. For the **engine** state read `aut2ltl/kr/STATUS.md`
(the FoSSaCS'22 cascade core); for construction history read `docs/HISTORY.md`.

## What works

The FoSSaCS'22 automaton→LTL construction is implemented end-to-end and
semantically validated. The portfolio front end (`reconstruct_decomposed`:
decompose/recombine + the sl heuristic gate over the acceptance-dispatch
cascade) sweeps the Manna–Pnueli class ladder — every probed case verifies
equiv=True. Details and the current size profile live in `aut2ltl/kr/STATUS.md`.

## How we drive it (main use case: the test scripts)

There is **no production entry point yet** — the package is exercised through
the placed scripts under `tests/` (mainly `tests/kr/`). That is the current
main use case; treat those scripts as the front door:

- `tests/kr/survey_mp_cascade.py` — MP-class × depth ladder, with Spot-equiv
  verdicts (the correctness gate). Run a single case: `… "G(p -> (q U r))"`.
- `tests/kr/survey_sizes.py` — size census (DAG/tree/temporal nodes) on the
  shipped `reconstruct_decomposed` path.
- `tests/kr/compare_sizes.py` — diff two `survey_sizes.py` logs for before/after.
- `tests/kr/test_kr_r4_audit.py` — structural audit gate (must stay CLEAN).

Persisted baselines live in `tests/kr/logs/`. See `aut2ltl/kr/README.md` for the
full tooling map.

## CLI

`aut2ltl/cli.py` is a **stub** — it currently wraps only the sl heuristic engine,
not the portfolio path. A real CLI over `reconstruct_decomposed` is upcoming work
(see `TODO.md`); until then, prefer the test scripts above.

## Layout

`aut2ltl/contract.py` (floor) ← `aut2ltl/kr` (pure cascade engine) +
`aut2ltl/sl` (heuristic engine) ← `aut2ltl/portfolio` (combinators) ←
`aut2ltl/cli`. Tests under `tests/` (`tests/kr`, `tests/sl`, `tests/fixtures`).
