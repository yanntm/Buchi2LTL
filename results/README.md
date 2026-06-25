# results — committed reference survey runs

Per-corpus reference runs of the **default** portfolio, one folder under
`reference/`. Each holds the per-formula CSV (GitHub renders it as a table) and a
one-glance `SUMMARY.txt`:

| corpus | folder | CSV | inputs |
|---|---|---|---|
| validation (the correctness gate) | `reference/validation/` | `default.csv` | 80 |
| benchmark (survey + W/U/R chains + Kinská) | `reference/benchmark/` | `default.csv` | 333 |
| Kinská on their own | `reference/kinska/` | `kinska.csv` | 165 |

Each CSV is keyed by its **`source`** column — the unique provenance of every row
(relative path / `file:line` / `--ltl:k`). The `input` column is the readable
label and may repeat.

## Refreshing a reference run (the evaluation gate)

Never overwrite a committed CSV blind. Rerun into the gitignored scratch `logs/`,
diff against the committed reference, and only overwrite when the diff is clean.

**Run every command below from the repo root, using the relative paths as written**
(`cd` to the root once, then never `cd` again — in particular do not `cd results/`,
or the relative `logs/...` paths drift and later steps fail).

```bash
# 1. rerun into a FRESH scratch (logs/ is gitignored; --logs writes a NEW
#    survey_<ts>.csv each run — wipe first so the survey_*.csv glob in steps 2-3
#    matches exactly one file and never an older stale run)
rm -rf logs/rerun
mkdir -p logs/rerun/{validation,kinska,benchmark}
python3 -m survey --folder samples/validation --logs logs/rerun/validation > logs/rerun/validation/SUMMARY.txt
python3 -m survey --folder samples/kinska     --logs logs/rerun/kinska     > logs/rerun/kinska/SUMMARY.txt
python3 -m survey --folder samples/benchmark  --logs logs/rerun/benchmark  > logs/rerun/benchmark/SUMMARY.txt

# 2. diff each new run against its committed reference (keyed on source; exits 1 on a regression)
python3 -m survey.diff.results results/reference/validation/default.csv logs/rerun/validation/survey_*.csv
python3 -m survey.diff.results results/reference/kinska/kinska.csv      logs/rerun/kinska/survey_*.csv
python3 -m survey.diff.results results/reference/benchmark/default.csv  logs/rerun/benchmark/survey_*.csv
```

**Clean** = each diff reports `0 regression(s)` and each `SUMMARY.txt` ends
`SUCCESS` (no verified non-equivalent / `FAIL`). A validation regression
(`TRUE -> ` anything else) makes the diff exit 1 — investigate, do not overwrite.
Size / technique movements are informational, a human judgement call.

```bash
# 3. only when clean: overwrite the committed CSV + summary, then commit
cp logs/rerun/validation/survey_*.csv results/reference/validation/default.csv
cp logs/rerun/validation/SUMMARY.txt  results/reference/validation/SUMMARY.txt
# …same for kinska/ and benchmark/…

# 4. clean up behind yourself so the next refresh starts from an empty scratch
rm -rf logs/rerun
```

Every step runs from the repo root with the relative paths exactly as written above —
do not `cd` into `results/` between steps (that drifts the `logs/...` paths and breaks
the diff/copy commands).
