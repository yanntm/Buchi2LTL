# aut2ltl.best_of — the choice-by-size brick

A single combinator, `best_of`, kept in its own package so the *idea* has a home and
a README — a primitive brick beside `first_success` and `recurse`, not a helper.

## What it is

```
best_of([a, b, c]) = walk a, b, c in order; keep the first OK as the trusted
                     incumbent; let a later OK take over only when `beats(...)` says so
```

A composite translator: the **size-objective** sibling of `first_success`. The whole
selection policy is one pluggable comparator, `beats(incumbent, challenger) -> bool`.

Package layout: `best_of.py` is the combinator (the walk); `comparators.py` is the
catalog of `Comparator` policies it can be configured with.

## Why a brick (and why beside `first_success`)

The portfolio is built from translators and a few **combinators** that compose them.
Two *choice* shapes recur — the difference is the selection rule:

- **choice by order** — `first_success([a, b, c])`: take the FIRST stage that
  succeeds. Cheap (stops at the first OK), but order-biased: the answer depends on
  who was cited first, not on which answer is best.
- **choice by size** — `best_of([a, b, c])`: run ALL the stages, hold the first OK as
  the trusted incumbent, and let a later one take over only when `beats(...)` says it
  wins. Pays for every branch, but selects on the objective we care about — output
  size — per input, *as guidance*: the first answer is trusted unless clearly beaten.

They are complementary, share one signature shape, and slot into the same seams.
`best_of` is what converts a recipe that wins on some inputs and loses on others
(e.g. an `inv`-woven variant) into **pure upside**: keep the trusted answer, and take
the alternative only on a real win — input by input, instead of committing globally.

## The comparator (the single pluggable seam)

A `Comparator` — `beats(incumbent, challenger) -> bool` — is the *one* place the policy
lives. **Intent:** every result `best_of` weighs denotes the SAME language (each is
faithful), so a comparator never changes *what* is expressed — it only picks a **better
FORM** of that language (smaller, better-factored, more readable). It compares two whole
`LTLResult`s, so a policy can weigh anything (size, a margin, temporals, technique), not
one scalar. The `Comparator` Protocol (`comparators.py`) pins the contract: total
(defined on formula-less results too), pure, tie-keeping (False ⇒ keep the incumbent),
and *sound by delegation* (it ranks already-faithful results, so it is a preference,
never a gate).

### The catalog (`comparators.py`)

| comparator | one-liner |
|---|---|
| `smaller` *(default)* | strict-min on DAG-node size; ties keep the incumbent |
| `significantly_smaller(rel, floor)` | switch only on a win ≥ `max(floor, ⌈rel·size⌉)` — strict on small instances, proportional on large |

`smaller` reads `dag_node_count(result.formula)`; the size is *derived in the
comparator*, not stored on `LTLResult`, so the contract floor stays free of the metric
layer. `significantly_smaller` is the *guidance* policy: DAG-node size is noisy at the
margin (a better-factored form can carry *more* nodes), so the trusted incumbent is
overridden only on a win large enough to trust the metric — tune `rel`/`floor` as it is
refined.

### Configuring / writing another comparator

Pass any `Comparator` as `beats`:

```python
from aut2ltl.best_of import best_of, significantly_smaller

best_of([trusted, challenger], name="guarded",
        beats=significantly_smaller(rel=0.2, floor=6))   # a tuned built-in
best_of([a, b], name="fewest_temporals",
        beats=lambda inc, ch: temporals(ch) < temporals(inc))   # an inline policy
```

To add a reusable one: write a function (or a factory returning one) in
`comparators.py` honouring the `Comparator` contract above, add it to that module's
`__all__`, and give it a row in the catalog table. Because it only chooses a form, no
soundness review is needed — `best_of` has already filtered to faithful results.

## Contract (the caller's obligation, and what is free)

- **Soundness is inherited.** Every stage is language-faithful or DECLINED (the
  Translator contract), so whichever OK result wins is still faithful — `best_of`
  cannot turn a sound portfolio unsound, whatever the `beats` comparator decides.
- **NOT_LTL short-circuits.** A NOT_LTL verdict from any stage is absorbing: the
  language is not LTL-definable, so no stage can produce a faithful formula and the
  verdict is returned at once (as in `first_success`).
- **Ties keep the earlier stage** — cited order is the tiebreak, so `best_of`
  degrades to `first_success` when all sizes are equal.
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
