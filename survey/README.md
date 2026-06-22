# survey — the aut2ltl evaluation harness

`survey` is a **client of aut2ltl**, not part of it. It *runs* examples through
the front-end tool and produces CSV + logs. It installs as the `aut2ltl_survey`
console tool, or runs as `python -m survey` from the repo root.

**Defaults** (all overridable — see [CLI](#cli)): verification **on**, per-input
budgets **15 s** build / **15 s** equivalence, the **default** technique, and the
CSV to **stdout** (pass `--logs DIR`, e.g. `--logs logs`, to write a file).

## Scope: run, don't curate

survey **runs and reports**; it does **not** author or curate corpora. Each
dataset owns its own curation, co-located under `samples/<set>/` — a sample
carries the scripts that build it, and they run fine installed or via `-m`.

The one exception is the dataset-agnostic **AP-normalization + dedup-key**
utility: every dataset's curation reuses it, so it lives here as
`survey/normalize` rather than being copied per sample.

## CLI

```
aut2ltl_survey [--ltl FORMULA] [--hoa FILE] [--folder PATH] \
               [--use TECH] [--logs DIR] [--no-verify] [--verbose] \
               [--build-timeout S] [--equiv-timeout S]
```

Inputs are explicit and **repeatable** — there are no bare positionals:

- `--ltl FORMULA` — an inline LTL/PSL formula.
- `--hoa FILE` — a HOA automaton file.
- `--folder PATH` — a file or directory, **recursed** for readable examples: HOA
  by content (any extension), or an LTL list one-formula-per-line in a
  `.ltl`/`.txt` file (`#` comments and blank lines skipped). `logs/`,
  `__pycache__/` and hidden dirs are pruned; unreadable / unrecognized files are
  skipped.

With no input given, usage is printed.

- `--use TECH` — **repeatable**, passed through opaquely. None given → the default
  technique. Several given → each is run over every example, all rows in **one
  flat CSV**, with a per-technique summary. The token `all` (every technique, for
  soundness coverage) needs runtime discovery and is **not yet supported**.
- `--logs DIR` — write the run's CSV here as `survey_<timestamp>.csv`; without it
  the CSV goes to **stdout**. The summary always prints to stdout.
- `--no-verify` — skip the spot-oracle equivalence check (on by default).
- `--verbose` — per-input live trace on stderr.
- `--build-timeout S` / `--equiv-timeout S` — per-input budgets (default 15s each).

survey is **agnostic to `--use` values**: it passes them through to the front end
and never enumerates or validates technique names — they evolve, and survey must
not track them. `all` is the sole token survey interprets, via discovery.

## Output (CSV)

One flat CSV per run; the columns, left to right, are a pipeline that
short-circuits — once a stage stops, the later cells stay empty:

| column | meaning |
|---|---|
| `input` | the example's display id — formula text (LTL) or file basename (HOA) |
| `result` | `LTL` / `NOT_LTL` / `PROBABLY_NOT_LTL` / `DECLINED` / `TIMEOUT` / `CRASH` |
| `technique` | the recipe that produced the answer |
| `build_s` | front-end wall time |
| `formula` | the reconstructed LTL (truncated), on `LTL` rows |
| `dag` `temporals` `tree` `sharing` | size metrics of that formula |
| `validation` | spot-oracle verdict — `TRUE` / `FAIL` / `SIZE` / `TIMEOUT` / `ERROR` / `OFF` |

The run is FAIL iff any row is verified non-equivalent (`validation == FAIL`);
otherwise SUCCESS (size/timeout/error are *not* failures). Each `Example` already
carries its `source` provenance (the originating `file[:line]`); emitting it as a
column is the CSV-provenance TODO below.

## Module map

| module | concern |
|---|---|
| `__main__.py` | `python -m survey` entry — delegates to `cli.main` |
| `cli.py` | argument parsing; gathers inputs → `Example`s, calls `run` |
| `run.py` | orchestrate examples × techniques → rows → CSV + per-technique summary |
| `example.py` | `Example` — one input (`kind`/`value`/`display`/`source` provenance) |
| `discovery/` | recurse `--folder` paths → readable examples (`walk` + `detect` + `read`) |
| `techniques.py` | resolve the `--use` set (pass-through; `all` → discovery — see TODO) |
| `bounded.py` | the `timeout --signal=INT --kill-after` subprocess primitive (one home) |
| `build.py` | run the front end on one example × technique via `bounded` → `BuildResult` |
| `verify.py` | **optional** spot-oracle equivalence (the gate's VERIFY), decoupled from build |
| `report.py` | CSV schema + writer + per-technique summary |
| `normalize/` | shared AP-normalization + dedup-key (its own [README](normalize/README.md)) |
| `diff/` | comparison tooling: **language** diff (`ltl_diff`/`diff_hoa`) + **result** CSV diff (`results`) — its own [README](diff/README.md) |

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

From the repo root: `python3 -m survey --folder samples/kinska --logs logs`.
Installed (after `pip install -e .`): `aut2ltl_survey --folder samples/kinska`.
