# tests/benchmark — portfolio evaluation bench

A **bench, not a gate**. Where `tests/survey*` checks the curated corpus stays sound,
this measures *output size* of one portfolio against another (first target:
`default` vs `best`) over a large, growing, structured input set — so we can see where
`best` wins/loses at scale before promoting it to the default.

It **reuses the survey engine**: `tests/survey.py` already runs `python3 -m aut2ltl`
per input (routing HOA vs LTL by content, `--use <recipe>`, strict per-input budget,
dense CSV), and `tests/survey_diff.py` already diffs two CSVs by DAG/tree size. The
bench adds the *inputs* and the A/B framing around that engine.

## Inputs (collected indiscriminately first, curated later)

- **`patterns.py`** — scalable structured families the random generator rarely hits:
  weak-until chains `φ W ψ W …`, strong-until chains, R/M chains, with `X`-insertions
  and non-trivial boolean/temporal arms. Parameterised by length.
- **`randltl`** — increasingly large `spot.randltl` formulas (growing `tree_size`),
  a few APs. We keep the ones that look *interesting* by result (curation, phase 2).
- **collected existing inputs** — `tests/fixtures/*.py` formula lists + `*.hoa`; the
  **Kinská** corpus under `tests/samples/kinska` (HOA automata + source LTL lists).

## Plan (phased — we are in phase 1)

1. **Collect** (now): generators + a manifest pointing at every input source. No
   filtering.
2. **Run + select**: sweep `default` vs `best`, keep inputs that are *interesting*
   (large delta, a regression, a size explosion, a decline).
3. **Curate** (later): syntactic **dedup** via AP-canonicalisation + a representative,
   roughly-classified committed set.

### AP-canonicalisation (the dedup key — phase 3)

Rename atomic propositions to `a, b, c, …` in order of **first occurrence in a
left-first DFS** of the formula tree, so two formulas that differ only by AP names
collapse to one syntactic key. We keep few APs and readable names; stay within
`a..e` (avoid clashing with the LTL operator letters `F G X U W R M` and the
constants — lowercase APs don't collide, but we cap low for readability).

## Layout

```
tests/benchmark/
  README.md       this plan
  patterns.py     structured pattern-family generators (phase 1)
  ...             manifest + runner + canonicaliser land as the phases do
```
