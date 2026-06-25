# recurse — the self-reference combinator (fix)

The fixpoint brick: it ties a one-level step into a recursive-descent translator.

## Setting

```
step    :  Translator → Translator
recurse :  (Translator → Translator) → Translator
```

`step(child)` is a translator that decomposes its input one level and delegates the
strictly-smaller sub-problems to `child`.

## Definition

```
recurse(step) = leaf      where    leaf = step(leaf)
```

The fixpoint of the endofunctor `step`: the translator that, on each call, behaves as
`step` applied to *itself*. `recurse` supplies no base case — termination and the floor
are `step`'s responsibility (the descent bottoms out when `step` stops delegating: an
atom, or a leaf translator that answers/declines without recursing).

## Example

The self-loop peel:

```
daisy(child) = recurse(λ leaf · first_success([ Daisy(leaf), child ]))
```

`Daisy(leaf)` peels one self-loop centre and recurses on its exits via `leaf`; if it
cannot peel, control falls to `child`.

## Properties

`recurse` adds no behaviour of its own: `leaf` is definitionally `step(leaf)`. It is
the *self-reference* complement of `first_success` (choice) among the primitive bricks
— the single seam the peels and the `decomp` composites share, where memoization
(`memo`) or a per-descent layer would later attach.

## Faithfulness

If `step` preserves faithful-or-⊥ given a faithful-or-⊥ child, its least fixpoint
`leaf` is faithful-or-⊥. (`recurse` itself is a pure knot-tier and contributes no
result.)

## Dependencies

The `Translator` type only (the floor). No engine; no behaviour beyond tying the knot.
