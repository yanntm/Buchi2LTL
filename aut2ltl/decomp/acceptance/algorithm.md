# The acceptance-conjunct decomposition algorithm

A composite translator that decomposes a language by the **conjuncts of its
acceptance condition**: on a deterministic automaton whose acceptance is `⋀_i c_i`,
it splits into one sub-language per conjunct — whose **intersection** is the original
— labels each, and recombines with `∧`, delegating an atomic (non-conjunctive)
acceptance to a leaf. It is the dual of the union decompositions (`decomp.scc`,
`decomp.strength`): an `∧` over acceptance conjuncts rather than an `∨` over
structural pieces.

## Setting

A translator maps a language to a label; this one is parameterized by the leaf `Λ`
it delegates to:

```
Label       =  Some φ  |  ⊥                  -- φ an LTL formula; ⊥ = decline
Translator  =  Language → Label
```

acceptance asks the Language for its **deterministic, generic, state-minimal** form
`A = detGenericMinimal(L)`:

- **deterministic** — the precondition the intersection identity needs (below); it is
  *established by the query*, never assumed of the input;
- **generic** — keeps the conjunctive generalized-Büchi (`⋀ Inf`) / Streett acceptance
  shape instead of collapsing it to parity, so the conjuncts survive to be read;
- **state-minimal** — fewer states feed whatever leaf labels the parts.

`A = (Q, Σ, δ, q0, acc)` with `acc = ⋀_{i=1..m} c_i` a top-level conjunction.

## The per-conjunct restriction

For conjunct `c_i`, let `A[acc := c_i]` be `A` with the **same** transition structure
but acceptance condition replaced by the single conjunct `c_i` (then acceptance-
cleaned). `L(A[acc := c_i])` is the words whose unique run meets `c_i`.

## The identity

```
L(A)  =  ⋂_{i=1..m}  L(A[acc := c_i])
```

exact **because `A` is deterministic**: each word has exactly one run, and that run
satisfies `⋀_i c_i` iff it satisfies every `c_i` — so a word is in `L(A)` iff it is in
every `L(A[acc := c_i])`.

> Determinism is required. On a nondeterministic automaton different conjuncts may be
> met by *different* runs of the same word, so `⋂_i L(A[acc := c_i]) ⊋ L(A)` — the
> intersection over-accepts. This is exactly why acceptance asks for the deterministic
> form rather than the bare TGBA.

It is an **intersection** — a pure position-0 language operation.

## The composite

```
acceptance(Λ) : Translator
acceptance(Λ)(L) =
    let A = detGenericMinimal(L); ⋀_i c_i = acc(A) in
    if m < 2 then Λ(L)                                   -- atomic acceptance: nothing to split
    else let φ_i = acceptance(Λ)( of(A[acc := c_i]) )    for each i
         in if any φ_i = ⊥ then ⊥                        -- a part we cannot label poisons it
            else Some( ⋀_i φ_i )
```

It recurses on **itself**, so the only thing reaching `Λ` is a single-condition
acceptance (the base case). The recombined label declines if any part declines: the
split is sound only when every part reconstructs. The recombined `∧` is simplified
(own rules) so cross-part folds and shared prefixes collapse.

## Termination

`A[acc := c_i]` carries the single condition `c_i`, not a conjunction, so it has no
top-level `∧` of ≥2: every recursive call drops to the base case. The split strictly
reduces the conjunct count (`m → 1`) and bottoms out in one level.

## Cost

The parts share the entire transition structure (only the acceptance differs), so the
conjuncts share everything but their fairness obligations: the hash-consed DAG dedups
the shared skeleton, the flat form repeats it. The split is an **enabler** — it turns
a multi-fairness automaton into an intersection of single-fairness languages a leaf
can crack — yet inflates the answer wherever the leaf already succeeds whole. So it
belongs under a cost / `best_of` gate that keeps it only when it converts a decline
into a smaller answer.
