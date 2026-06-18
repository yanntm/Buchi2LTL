# aut2ltl.best_of — the choice-by-size brick

A single combinator, `best_of`, kept in its own package so the *idea* has a home and
a README — a primitive brick beside `first_success` and `recurse`, not a helper.

## What it is

```
best_of([a, b, c], key=cost) = the OK result among a, b, c with the least cost
```

A composite translator: run every stage, keep the smallest language-faithful result.
It is the **size-objective** sibling of `first_success`.

## Why a brick (and why beside `first_success`)

The portfolio is built from translators and a few **combinators** that compose them.
Two *choice* shapes recur — the difference is the selection rule:

- **choice by order** — `first_success([a, b, c])`: take the FIRST stage that
  succeeds. Cheap (stops at the first OK), but order-biased: the answer depends on
  who was cited first, not on which answer is best.
- **choice by size** — `best_of([a, b, c])`: run ALL the stages and take the
  SMALLEST. Pays for every branch, but selects on the objective we actually care
  about — output size — per input.

They are complementary, share one signature shape, and slot into the same seams.
`best_of` is what converts a recipe that wins on some inputs and loses on others
(e.g. an `inv`-woven variant) into **pure upside**: keep the cheaper of the two,
input by input, instead of committing to one globally.

## The cost

The default `key` is `LTLResult.cost` — the **DAG-node count** of the result formula
(what the survey and benchmark report as "DAG nodes"), which is the portfolio's
minimization objective. `cost` is a derived, lazily-computed field on `LTLResult`
(`result.py`); a `None` cost (no formula) sorts as +∞ and never wins. Pass a custom
`key` to select on a different measure.

## Contract (the caller's obligation, and what is free)

- **Soundness is inherited.** Every stage is language-faithful or DECLINED (the
  Translator contract), so the least-cost OK result is still faithful — `best_of`
  cannot turn a sound portfolio unsound, whatever the `key`.
- **NOT_LTL short-circuits.** A NOT_LTL verdict from any stage is absorbing: the
  language is not LTL-definable, so no stage can produce a faithful formula and the
  verdict is returned at once (as in `first_success`).
- **Ties keep the earlier stage** — cited order is the tiebreak, so `best_of`
  degrades to `first_success` when all costs are equal.
- **Cost, not free.** `best_of` runs *every* applicable stage (no short-circuit on
  the first OK). Use it where the size win justifies the extra runs; keep
  `first_success` where order already encodes priority and the first answer is fine.

## Functional, on purpose

Like `first_success`, the composite is a named callable (`name` is its identity, not
a technique) that returns the winning child's `LTLResult` **unchanged** — it stamps
no tag of its own and accumulates no state. The selection is a fold over the stages,
not a class hierarchy.

## The seam it opens

`best_of` shares `first_success`'s shape, so a `recurse` step that today reads
`first_success([Daisy(leaf), …, floor])` can later read `best_of([…])` to pick the
smallest peel per descent — the per-level size choice the `recurse` README flags as
a future lever. (See `aut2ltl/recurse/README.md` and `aut2ltl/portfolio/README.md`.)
