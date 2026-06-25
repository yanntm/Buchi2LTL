# best_of — the choice-by-size combinator (⊞)

A composite translator that evaluates every stage and selects one by a pluggable
comparator, keeping the first as a trusted incumbent.

## Setting

```
stages   t₁ … tₙ  :  X → LTLResult            -- generic in the input X
beats    :  LTLResult × LTLResult → Bool      -- the Comparator (incumbent, challenger)
⊞[t₁…tₙ ; beats] :  X → LTLResult
```

## Definition

Walk the stages in order, maintaining an incumbent:

```
⊞[t₁…tₙ ; beats](x):
    inc ← none
    for t in t₁…tₙ:
        r ← t(x)
        if not_ltl(r):        return r          -- absorbing verdict
        if declined(r):       continue
        if inc = none:        inc ← r           -- the trusted first OK
        else if beats(inc, r): inc ← r          -- a winning challenger takes over
    return inc if inc ≠ none else ⊥
```

Contrast with `⊕` (`first_success`): `⊕` stops at the first `OK`; `⊞` evaluates all
arms and selects by `beats`. A `NOT_LTL` from any stage is absorbing.

## The comparator

The entire policy is the one injected `beats`; the walk is fixed. Provided:

- `smaller` — strict minimum of DAG-node size.
- `significantly_smaller(rel, floor)` — *guidance*: the first-cited answer is trusted
  (expected at least as good on grounds the metric cannot see — factoring,
  readability) and is overridden only by a win past a relative + absolute margin.

## Example

`⊞[best_daisy2, rich]` (the `cake` family): the cascade-flooring incumbent is kept
unless the cheap `PartScc`-only `rich` arm is *significantly* smaller.

## Faithfulness

Every arm is faithful-or-⊥ by contract; the returned arm is one of them, unchanged.
Soundness is therefore independent of the comparator — `beats` only chooses *which*
sound form to keep.

## Dependencies

The combinator needs only `aut2ltl.result.LTLResult` (the floor). The comparator is a
parameter; the provided size comparators read `dag_node_count` from `aut2ltl.ltl`
metrics. That module is engine-agnostic (Spot-only), so `best_of` takes on no
dependency on any concrete contract realization, and the metric is swappable.
