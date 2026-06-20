# survey — the aut2ltl evaluation harness

`survey` is a **client of aut2ltl**, not part of it. It *runs* examples through
the front-end tool and produces CSV + logs. It installs as the `aut2ltl_survey`
console tool, or runs as `python -m survey` from the repo root.

## Scope: run, don't curate

survey **runs and reports**; it does **not** author or curate corpora. Each
dataset owns its own curation, co-located under `samples/<set>/` — a sample
carries the scripts that build it, and they run fine installed or via `-m`.

The one exception is the dataset-agnostic **AP-normalization + dedup-key**
utility: every dataset's curation reuses it, so it lives here as
`survey/normalize` rather than being copied per sample.

## CLI

```
aut2ltl_survey PATH [PATH ...] [--logs DIR] [--use TECH ...]
```

- `PATH ...` — files or folders, **recursed** for readable examples (HOA by
  content, LTL one-per-line in `.ltl`); unreadable / unrecognized files skipped.
- `--logs DIR` — where CSV + summaries go (**default `./logs`**).
- `--use TECH` — **repeatable**. None given → the default technique only. Each
  given → its own run + CSV (A/B/N-way comparison). The token `all` runs **every**
  technique (soundness coverage).

survey is **agnostic to `--use` values**: it passes them through to the front end
and never enumerates or validates technique names — they evolve, and survey must
not track them. `all` is the sole token survey interprets, via discovery.

## Module map (bones to fill)

| module | concern |
|---|---|
| `__main__.py` | entry: parse args; orchestrate examples × techniques → CSV |
| `discovery/` | recurse PATHs → readable examples (small files: `walk` + `detect` + `read`) |
| `techniques.py` | resolve the `--use` set (pass-through; `all` → discovery — see TODO) |
| `bounded.py` | the `timeout --signal=INT --kill-after` subprocess primitive (one home) |
| `build.py` | run the front end on one example × technique via `bounded` → `BuildResult` |
| `verify.py` | **optional** spot-oracle equivalence (the gate's VERIFY), decoupled from build |
| `report.py` | CSV schema + writer + summary (was `survey_summary`) |
| `normalize/` | shared AP-normalization + dedup-key (to migrate in from `tests/benchmark/normalize`) |
| `diff/` | comparison tooling: **language** diff (`ltl_diff`/`diff_hoa`) + **result** CSV diff (`results`) |

Old → new: `survey.py` splits into `discovery` + `build` + `verify`;
`survey_diff.py` → `survey.diff.results`; `survey_summary.sh` → `report`; the
`*_sweep.sh` shells dissolve into `__main__`'s multi-`--use` loop;
`kinska_breakdown.py` is retired in favour of CSV-native provenance (see TODO).

## TODO

- **`--use all` → technique discovery.** survey must enumerate the available
  techniques from the portfolio registry **at runtime** (no hardcoded list) and
  run them all for soundness. Until that lands, `all` is unsupported.
- **CSV provenance.** Carry each example's source subfolder in the CSV natively,
  so per-folder breakdowns need no input-order replay (this is the whole reason
  `kinska_breakdown.py` existed).

## Running

From the repo root: `python -m survey samples/validation --logs ./logs`.
Installed: `aut2ltl_survey samples/validation`.
