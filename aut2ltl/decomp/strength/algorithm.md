# The strength decomposition algorithm

A composite translator that decomposes a language by automaton **strength**: it
splits into a weak, a terminal, and a strong sub-language — whose union is the
original — labels each, and recombines with `∨`, delegating a single-strength
language to a leaf. It is the coarse, strength-bucket cousin of the per-SCC split
(`decomp.scc`): one piece per Manna–Pnueli strength rather than one per accepting
SCC.

## Setting

A translator maps a language to a label; this one is parameterized by the leaf `Λ`
it delegates to:

```
Label       =  Some φ  |  ⊥                  -- φ an LTL formula; ⊥ = decline
Translator  =  Language → Label
```

strength asks the Language for its **TGBA** form `A = tgba(L)`. It manipulates only
the SCC structure (via Spot's strength decomposition), so no determinism is assumed
or required — the union below is exact on a nondeterministic automaton.

## Strengths

Spot's strength decomposition (Renault, Duret-Lutz, Kordon, Pommereau, TACAS'13)
classifies each SCC and extracts, for each **strength** `k ∈ {weak, terminal,
strong}`, the sub-automaton `decompose_scc(A, k)` that keeps the runs whose accepting
behaviour is of that strength:

- **weak** — accepting via a weak (no proper accepting cycle structure) component;
- **terminal** — accepting via a terminal SCC (reach-and-stay, a guarantee);
- **strong** — accepting via a genuinely strong (Büchi-recurrent) SCC.

A sub-automaton with no states is absent. Write `strengths(A)` for the non-empty ones.

## The identity

```
L(A)  =  ⋃_{k ∈ strengths(A)}  L(decompose_scc(A, k))
```

exact for **any** automaton (TACAS'13): an accepting run's strength is well-defined,
so it accepts in exactly the sub-automaton of its own strength (⊆); and each
sub-automaton keeps a subset of `A`'s accepting behaviour (⊇). It is a **union** — a
pure position-0 language operation, exact on a nondeterministic automaton
(`L(⋃) = ⋃ L`), needing no determinization.

## The composite

```
strength(Λ) : Translator
strength(Λ)(L) =
    let A = tgba(L); {k_1,…,k_n} = strengths(A) in
    if n < 2 then Λ(L)                                  -- single-strength: nothing to split
    else let φ_j = strength(Λ)( of(decompose_scc(A, k_j)) )  for each j
         in if any φ_j = ⊥ then ⊥                       -- a part we cannot label poisons it
            else Some( ⋁_j φ_j )
```

It recurses on **itself**, so the only thing reaching `Λ` is a single-strength
language (the base case). The recombined label declines if any part declines: the
split is sound only when every part reconstructs. The recombined `∨` is simplified
(own rules) so overlapping parts and shared prefixes fold.

## Termination

`decompose_scc(A, k)` keeps only the runs of strength `k`, so its result is
single-strength: `strengths(decompose_scc(A, k)) = {k}`, of size 1. Every recursive
call therefore drops to the base case — the split strictly reduces the strength count
(`n → 1`) and bottoms out in one level.

## Cost

The pieces share the structure leading into their accepting region, so the disjuncts
share prefixes: the hash-consed DAG dedups them, the flat form repeats them. The
split is an **enabler** — it turns a mixed-strength automaton into a union of
single-strength languages a strength-specialized leaf can crack — yet inflates the
answer wherever the leaf already succeeds whole. So it belongs under a cost /
`best_of` gate that keeps it only when it converts a decline into a smaller answer.
