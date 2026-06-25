# aut2ltl.recurse — the recursive-descent brick

A single combinator, `recurse`, kept in its own package so the *idea* has a home
and a README — a primitive brick beside `first_success`, not a pile of helpers.

## What it is

```
recurse(step) = leaf   where   leaf = step(leaf)
```

The least fixpoint of a **Translator endofunctor**. `step(child)` is a one-level
decorator — decompose the input, hand each strictly-smaller sub-problem to
`child`, recombine — and `recurse` ties the knot by passing `step` a reference to
the translator it is building, so `child` *is* the whole recursion.

## Why a brick (and why beside `first_success`)

The portfolio is built from translators and a few **combinators** that compose
them. Two shapes recur:

- **choice** — `first_success([a, b, c])`: a FLAT chain of distinct translators,
  take the first that succeeds.
- **recursion** — `recurse(step)`: a SINGLE translator that contains *itself*.

`first_success` cannot express the self-reference; `recurse` cannot express the
chain. They are complementary, and they compose — the base case of a recursion is
just a floor rung of a `first_success` *inside* `step`:

```python
daisy_pair(floor) = recurse(
    lambda leaf: first_success([Daisy(leaf), Daisy2(leaf), floor], name="daisy_pair")
)
```

`daisy`, `daisy_pair`, and the strength / acceptance / scc decomposers are all
this one shape (decompose → recurse on smaller sub-problems → recombine). Factoring
it out gives **one place** to later add the levers that shape needs:

- `best_of` instead of `first_success` (size is the objective — pick the smallest
  child, not the first);
- memoization on the `Language` (free DAG sharing across the descent);
- a per-descent layer (e.g. applying the invariant strip `inv` at *every* level,
  where it actually earns its keep — not just once at the top).

## Contract (the caller's obligation)

`recurse` is a **pure knot-tier**: it adds no base case and no behaviour beyond the
self-reference. Two obligations live in `step`, not here:

- **Termination.** Every sub-problem `step` delegates to `child` must be strictly
  smaller (well-founded descent). A `step` that recurses on an input no smaller
  will not terminate.
- **Base case / floor.** Where nothing decomposes, `step` must answer (or decline)
  itself — typically via a floor rung of a `first_success`.

**Soundness** is inherited from the Translator contract: every `LTLResult` that
flows is language-faithful or declined, never wrong, so the fixpoint is sound by
construction whatever `step` does.

## Functional, on purpose

The whole thing is `def leaf(lang): return step(leaf)(lang)` — a Y-combinator in
one line. Under this framing the recursion is a value, not a class hierarchy: there
is no base/derived split, no visitor, no mutable "current node". The OO idioms that
would model "a recursive decomposition strategy" as a class collapse to a closure
that names itself.
