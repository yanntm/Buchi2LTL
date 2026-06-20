# tests/

The test and data-collection harness. Everything runs the engine through the
real front end (`python3 -m aut2ltl`), so it tests what a user runs. Subdirs with
their own README (`bls/`, `fixtures/`, `samples/kinska/`) keep the detail; this
file is just the index.

## Ground rules

- Run from the project root; scripts put the root on `sys.path` themselves.
- Placed scripts only — no `/tmp`, no `python -c` one-liners (see `CLAUDE.md`).
- Each case runs in its own `-m aut2ltl` subprocess under a STRICT per-phase
  budget (15s, `KR_SURVEY_TIMEOUT`). The budget is enforced with
  `timeout --signal=INT --kill-after=1`, so a runaway GAP child is reaped by the
  interrupt handler in `aut2ltl/proc.py` (then SIGKILLed after a 1s grace) and
  never orphaned. A blown budget IS a finding (reported `BUILD_TIMEOUT`), not a
  failure to wait on.
- Run logs are never committed, except the curated baseline under
  `logs/reference/` (and `samples/kinska/logs/reference/`).

## Gate before committing engine changes

    python3 -m tests.probes.bls.test_kr_r4_audit     # must report CLEAN
    python3 tests/survey.py                  # must end SUCCESS (no verified non-equiv)

## Survey & sweeps (end-to-end data collection)

- `survey.py` — the single survey: per case, BUILD via the CLI tool then VERIFY
  via a test-only spot oracle (classify + `are_equivalent`). The SUCCESS gate.
- `survey_sweep.sh` — sweep `survey.py` across `--use` configurations
  (techniques/flags head-to-head) on the curated corpus; per-config CSV + `.txt`
  and a cross-config `SUMMARY.txt`.
- `survey_summary.sh <dir>` — (re)build that `SUMMARY.txt` from the per-config
  CSVs already in a dir, re-running no tool. The sweep calls it for its summary
  step (single source of truth), and it recovers the summary for an OLD
  reference folder whose per-config `.txt` was never kept.
- `kinska_sweep.sh` — `survey.py` over the Kinská sample corpus
  (`samples/kinska/`) with the DEFAULT portfolio only, strict 15s/run, one flat
  log (`kinska.csv`/`.txt` + `SUMMARY.txt`) into `samples/kinska/logs/reference/`.
- `survey_formulas.py` — the curated survey corpus, in isolation (the formula
  list `survey.py` sweeps when given no inputs).
- `survey_diff.py` — quantitative diff of two survey CSVs (regression triage).

### Where they build & how to run them

Each sweep takes an OUTPUT DIR as `$1` and writes per-config (or per-input) CSVs
there plus a `SUMMARY.txt`; pass a throwaway dir under `tests/logs/` (gitignored)
for day-to-day runs. Both sweeps self-terminate, so launch them in the background
(parallel is fine — they are CPU-bound and independent) and wait on completion:

    bash tests/survey_sweep.sh tests/logs/scratch_survey   # all --use configs, LTL corpus
    bash tests/kinska_sweep.sh tests/logs/scratch_kinska    # default portfolio, Kinská corpus

Read `SUMMARY.txt` first; it must print `SUCCESS` (no verified non-equivalence;
`BUILD_TIMEOUT` / `UNVERIFIED_SIZE` are size explosions, not failures).

### Promoting a sweep to the committed reference baseline

The reference is CSV-only, under dated subfolders. After a run is green, diff it
against the current reference with `survey_diff.py` per config (look for `0
regression(s)`), then promote:

- **survey** — copy the new per-config CSVs to a NEW dated folder
  `tests/logs/reference/<YYYYMMDD>/` (append `_1`, `_2`, … only to DISAMBIGUATE a
  same-day collision — the clean date is the canonical/newest baseline). Or just
  point the sweep straight at the new folder. The `.gitignore` re-includes
  `tests/logs/reference/**/*.csv` plus the token-compact `SUMMARY.txt` and the
  per-config `.txt`, so commit those too (`sweep.log`, the bulky per-formula
  stderr trace, stays ignored). For older folders that predate keeping the
  `.txt`, regenerate just the summary with `survey_summary.sh <folder>`.
- **kinská** — overwrite `tests/samples/kinska/logs/reference/kinska.csv` (and its
  `.txt` / `SUMMARY.txt`) in place (single flat baseline; git history keeps the
  prior). Squash in place once green on size/results vs. the current reference.

Then commit the baseline move as ONE commit (it is a bulk log regeneration, the
exception to one-commit-per-file). Logs are otherwise never committed.

## Unit / smoke tests (fast, mostly GAP-free)

- `test_build_portfolio.py` — building a `Translator` triggers NO GAP.
- `test_contract_combinators.py` — the pure contract-floor combinator algebra.
- `test_language.py` — the contract-floor `Language` constructors build
  language-equivalent automata from both an automaton and an LTL source.
- `test_ltl_metrics.py` — `ltl.metrics` + `ltl.printers`.
- `test_options.py` — the contract-floor `Options` flags compartment.
- `test_sl_member.py` — the `Sl` Translator either declines or returns a
  language-equivalent formula (sound by construction).

## Folders

- `bls/` — development & verification scripts for the `bls/` algebraic path
  (audit, tracing, language-diff tools). See `bls/README.md`.
- `sl/` — case-finder probes for the heuristic `sl` engine (f2/t2 SCC patterns)
  plus debug artifacts.
- `fixtures/` — interesting LTL formulas and HOA automata used in development.
  See `fixtures/README.md`.
- `samples/` — external benchmark corpora. `samples/kinska/` is the Kinská
  thesis Büchi automata + source formulae (see its README).
- `logs/` — survey run outputs; throwaway except the committed `reference/`
  release baseline.
