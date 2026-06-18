# Benchmark samples — Kinská

Benchmark Büchi automata (HOA format) and their source LTL formulae, adopted as
test inputs for our automata→LTL construction.

## Provenance

- **Source:** <https://gitlab.fi.muni.cz/xkinska/master-thesis-implementation>
  (commit `1a1b45d`, 2025-05-20)
- **Author:** Tereza Kinská
- **Thesis:** *Detection of LTL-Definability in Büchi Automata*, Master's thesis,
  Faculty of Informatics, Masaryk University (FI MUNI), Brno, Spring 2025 —
  [report (PDF)](https://is.muni.cz/th/svrfk/master_thesis_TK_Archive.pdf).
- **Tool:** `ba2ltlDecider`

Quoted from the source repository's README:

> This tool was created as a part of masters thesis at FI MUNI. It was created
> with an aim to make it a part of the Spot library.

## License

The source repository carries a GNU GPLv3 / AGPLv3 license (its README states GNU
GPL v3 "the same as the license of Spot"; its `LICENSE` file is the GNU Affero
GPL v3). Both are compatible with this project's GPLv3 license. Copyright (c)
2025 Tereza Kinská.

## Layout

Mirrors the upstream `experiments_data/` directory:

- `counting/{1ap,2ap}/` — counting Büchi automata.
- `randltl/{1,2,4,8}ap-ba/` — random-LTL Büchi automata, with the source formula
  lists in the sibling `*-formulae/` directories.

## Our results on this corpus (2026-06-15, preliminary)

Full detail (per-input formula, sizes, verdict) is in
[`logs/reference/kinska.csv`](logs/reference/kinska.csv) +
[`SUMMARY.txt`](logs/reference/SUMMARY.txt).


A like-for-like comparison (our aperiodicity gate vs their decider, per instance,
and whether our 8 validated cases fall in their confirmed-51 or timed-out-34) is
left for a dedicated follow-up.
