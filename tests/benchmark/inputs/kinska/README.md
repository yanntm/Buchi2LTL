# kinska — Büchi automata (HOA)

105 unique Büchi automata in HOA format, imported (flattened + `.txt`→`.hoa`) and
deduped from the 125 under `tests/samples/kinska` via the normalised-AP key
(`tests/benchmark/normalize.normalize_hoa`); 20 cosmetic/exact duplicates dropped
(her 1-AP randltl sampling is heavily redundant). Her `*-formulae/` LTL files are
**not** imported — they are the randltl sources of the `-ba` automata, redundant
with the HOA kept here. Flat names encode her original path
(`<group>-<subdir>-<leaf>.hoa`).

Regenerate: `python3 tests/benchmark/collect_kinska.py`.

Many of these are **not LTL-definable** (the corpus exists to test definability
detection) — the construction correctly DECLINES on those; that is recorded as
`NOT_LTL`, not a failure.

## Provenance / license

From Tereza Kinská, *Detection of LTL-Definability in Büchi Automata* (MSc, FI MUNI,
2025), tool `ba2ltlDecider` — see `tests/samples/kinska/README.md` for the full
citation and the GPLv3/AGPLv3 license. Copyright (c) 2025 Tereza Kinská.
