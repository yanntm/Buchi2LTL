# The deep_roundtrip algorithm

A `Rewriter` that **re-presents the whole formula DAG, bottom-up**. `deep_roundtrip(R)`
folds the re-presentation `R` over every node: a node is re-presented from its
*already re-presented* children, in one memoized post-order pass.

## Setting

```
Rewriter  =  LTLResult → LTLResult
R         :  Rewriter               -- the per-node re-presentation (e.g. best_of([identity, relabel(Λ)]))
```

No finder `Φ` and no cut node — the whole-DAG peer of `roundtrip` (one located node)
and `roundtrip_decomp` (a located node's operands). The descent IS the search.

## The construction

```
deep_roundtrip(R) : Rewriter
deep_roundtrip(R)(r) =
    let memo = {} in
    let go(n) =
          if n ∈ memo then memo[n]
          else let n' = n⟨ go(c) for c ∈ children(n) ⟩    -- rebuild from re-presented children
               and p  = R(success(n'))
               in  memo[n] := (p.formula if p ok else n');  memo[n]
    in  let φ' = go(r.formula) in
        if φ' = φ then r                                   -- all no-op → unchanged, uncredited
        else start(tag).credit(r).credit(each p) with formula φ'
```

## Why bottom-up, and why one pass

The root of a blown-up result is over the translate bound, so a top-down round trip
cannot even start. Bottom-up, a child re-presented *smaller* shrinks its parent, which
may then drop under the bound and become re-presentable in turn — the collapse climbs
from the leaves. Because each parent is visited *after* its children are settled, a
single post-order pass propagates the whole way up; no outer fixpoint is needed.

## DAG-complexity (the memo)

The memo is one per-call `dict` keyed on the `spot.formula` itself. Formulas are
hash-consed — equal structure is the same object — so structural identity *is* the key:
each distinct node is re-presented exactly once, the heavily-shared hubs included. The
re-presented results re-intern into the same hash-consed DAG, so sharing is preserved
and the output stays compact; `subst`-style identity propagation rides the same table.

## Faithfulness and attribution

`R` is a Rewriter, so each `R(success(n')) ≡ n'` (or declines, keeping `n'`); by
congruence every node stays ω-equivalent under its context, so `φ' ≡ φ`. With `R`
never-regress-floored (`best_of([identity, …])`) no node grows. An all-no-op pass
returns `r` verbatim, uncredited (the `ltl_rewriter` attribution rule).
```
