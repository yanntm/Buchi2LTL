# tests/benchmark — portfolio evaluation bench

A **bench, not a gate**. Where `tests/survey*` checks the curated 40-formula corpus
stays sound, this measures *output size* of one portfolio against another (first
target: `default` vs `best`) over a large, growing, structured input set — to see
where `best` wins/loses at scale before promoting it to the default.

It **reuses the survey engine**: `tests/survey.py` runs `python3 -m aut2ltl` per input
(routing HOA vs LTL by content, `--use <recipe>`, strict per-input budget, dense CSV;
its summary separates *what aut2ltl answered* from *what Spot could verify*), and
`tests/survey_diff.py` diffs two CSVs by DAG/tree size + equiv transitions. The bench
adds the *inputs*, the A/B framing, and the dedup key around that engine.

## Running

```
tests/benchmark/bench_sweep.sh                          # whole corpus -> tests/benchmark/logs
tests/benchmark/bench_sweep.sh OUTDIR PATHS...          # subset (dirs/files), dev
KR_SURVEY_TIMEOUT=8 tests/benchmark/bench_sweep.sh      # tighter per-input budget
```

Writes `default.csv` / `best.csv` (+ `*.txt` summaries, `*.sweep.log`) into the output
dir and prints the default-vs-best size diff. `tests/benchmark/logs/` is gitignored
(throwaway); committed reference runs live in `tests/benchmark/logs/reference/`.

## Inputs (`inputs/`, raw files — no python)

Category subfolders, each holding `.ltl` (one formula per line, `#` comments) or `.hoa`
(one automaton); `.md` is ignored by the sweep. See `inputs/README.md` for the format.
Generators live *outside* `inputs/` and emit committed files into it:

- **`inputs/core/`** — the curated 40-formula survey corpus, one `.ltl` per MP class
  (`from_survey.py`). The bench's seed; reproduces the survey exactly.
- **`inputs/chains/`** — scalable W/U/R chains with optional `X`-lacing and W-U/U-R
  mixes, over non-trivial arms (`patterns.py --emit`).
- **`inputs/kinska/`** — 105 Büchi automata (HOA), flattened + deduped from the 125
  under `tests/samples/kinska` (`collect_kinska.py`); many are not LTL-definable.

## Tools

- **`patterns.py`** — chain-family generator (`--emit DIR`).
- **`from_survey.py`** — mirror the survey corpus into `inputs/core/`.
- **`collect_kinska.py`** — import + dedup Kinská HOA into `inputs/kinska/`.
- **`normalize.py`** — AP-canonical NAME form (the dedup key): renames APs to `a,b,c…`
  by first occurrence and NOTHING else (no simplification/reordering). LTL + HOA.
  `--dedup PATHS...` reports duplicate groups.

## Plan (phased)

1. **Collect** (done for core/chains/kinska): generators + collectors, no filtering.
2. **Run + select**: sweep `default` vs `best`, keep inputs that are *interesting*
   (large delta, a regression, a size explosion, a decline).
3. **Curate**: dedup (via `normalize.py` — already the import key) + a representative,
   roughly-classified set; grow the random `randltl` ladder *very* progressively (the
   construction is multiply-exponential — lean on the per-input timeout).
