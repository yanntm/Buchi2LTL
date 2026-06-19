# normalize — AP-normalisation + dedup services

A small, self-contained tool: canonicalise the atomic propositions of LTL formulas
and HOA automata, and dedup a folder of them. It is **orthogonal to sample
collection** — it does not generate a corpus. Dedup reports by default (dry run);
its `--prune` is the explicit opt-in that removes the duplicates.

## Services

- **`names.py`** — rename APs to `a, b, c…` in order of first occurrence, nothing
  else. `normalize_ltl` / `normalize_hoa` / `normalize_text` (content dispatch).
- **`polarity.py`** — complement each AP so its first literal occurrence is positive,
  nothing else (`!a X F a` and `a X F !a` both fold to `a X F !a`).
  `polarity_normalize_ltl` / `polarity_normalize_hoa` / `polarity_normalize_text`.
- **`dedup.py`** — walk a folder, split each file into items (one per HOA, one per
  non-comment line per `.ltl`), keep the first item per **pluggable** key, drop the
  rest. Reports per-file drop counts by default; `--prune` deletes / rewrites.

The two normalisers are independent (one touches names, the other signs), so they
compose freely. `dedup.default_key` is `polarity ∘ names`.

## CLI

```
python3 names.py    '<formula>' | file.hoa | file.ltl   # print normalised form
python3 polarity.py '<formula>' | file.hoa | file.ltl   # print polarity-canon form
python3 dedup.py FOLDER                                  # dry run: per-file drop counts
python3 dedup.py --prune FOLDER                          # apply: delete / rewrite dups
```

## Test

```
python3 test_polarity.py        # OK / raises
```
