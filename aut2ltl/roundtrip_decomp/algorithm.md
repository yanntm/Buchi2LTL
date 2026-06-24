# The roundtrip_decomp algorithm

A `Rewriter` that **re-presents the operands of one node**. Given a `Rewriter` `R` and
a node finder `Φ`, it locates `N = Φ(φ)`, re-presents each operand of `N` with `R`, and
rebuilds `N` from the results. When `N` is a `∧` / `∨` this is the formula-space
decomposition `L(N) = ⋂/⋃ L(ψᵢ)` — each conjunct / disjunct re-derived on its own
simpler automaton, a split the formula carries *syntactically* that the product
automaton hides; for any other operator it is operand re-presentation.

## Setting

```
Rewriter  =  LTLResult → LTLResult
R         :  Rewriter               -- the per-operand re-presentation
Φ         :  Formula → (Node | ⊥)   -- locates the node whose operands are re-presented
```

`operands(N) = ψ₁ … ψₖ` are `N`'s distinct immediate children. `N⟨ψ₁' … ψₖ'⟩` is `N`
rebuilt with its operands replaced by `ψ₁' … ψₖ'`, and `φ[N ↦ N']` substitutes by
hash-consed identity (`roundtrip/subst`).

## The construction

```
roundtrip_decomp(R, Φ) : Rewriter
roundtrip_decomp(R, Φ)(r) =
    let φ = r.formula; N = Φ(φ) in
    if N = ⊥ then r                                  -- nothing to decompose
    else  let ψᵢ' = R( success(ψᵢ) )  for ψᵢ ∈ operands(N)   -- re-present each operand
          and  N'  = N⟨ψ₁' … ψₖ'⟩                              -- rebuild N from the results
          in   if N' = N  then r                               -- no operand improved → unchanged
               else  start(tag).credit(r).credit(ψ₁' … ψₖ')  with formula  φ[N ↦ N']
```

A declined operand re-presentation declines the result; an `identity`-floored `R`
(`best_of(identity, …)`) never declines, so the result is `r` unchanged or a smaller
faithful formula.

## Independent operands, single rebuild

Each operand is re-presented as a **standalone formula**, and `N` is reassembled in one
edit. The operands are mutually independent — re-presenting one neither reads nor
alters another — so the rewrites are order-free, and no hash-cons identity is touched
until the single `φ[N ↦ N']`. Soundness needs only **per-operand** faithfulness:
`R(success(ψᵢ)) ≡ ψᵢ` (the Rewriter contract), hence `N' ≡ N` by congruence and
`φ[N ↦ N'] ≡ φ` — even when operands share subformulas, since each is independently
faithful.

## The climb

With `R = roundtrip_decomp(…)` tied through `recurse`, each operand is decomposed before
it is re-presented, so the re-derivation compounds bottom-up — a node is re-presented
from already-simplified descendants. The flat case is `R = best_of(identity, relabel(Λ))`.
