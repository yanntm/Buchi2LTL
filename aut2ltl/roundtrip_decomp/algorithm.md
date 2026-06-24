# The roundtrip_decomp algorithm

A `Rewriter` that **re-presents every operand of one node**. Given a per-operand
rewriter `R` and a node finder `Φ`, it locates `N = Φ(φ)` and replaces each operand
`ψᵢ` of `N` by `R`'s re-presentation of it, in place. When `N` is a `∧` / `∨` this is
the formula-space decomposition `L(N) = ⋂/⋃ L(ψᵢ)` — each conjunct/disjunct re-derived
on its own simpler automaton, a split the formula gives *syntactically* that the
product automaton hides; for any other node it is the (still sound) operand
re-presentation.

## Setting

```
Rewriter  =  LTLResult → LTLResult
R         :  Rewriter               -- the per-operand re-presentation
Φ         :  Formula → (Node | ⊥)   -- locates the node whose operands are re-presented
```

`operands(N)` are `N`'s immediate children `ψ₁ … ψₖ`; `φ[ψ ↦ ψ']` substitutes by
hash-consed identity (`roundtrip/subst`).

## The construction

```
roundtrip_decomp(R, Φ) : Rewriter
roundtrip_decomp(R, Φ)(r) =
    let φ = r.formula; N = Φ(φ) in
    if N = ⊥ then r                               -- nothing to decompose
    else  let out = start(tag).credit(r);  φ' = φ  in
          for each ψ ∈ operands(N):
              let p = R( success(ψ) ) in
              out.credit(p)                        -- fold the operand's provenance
              φ' := φ'[ ψ ↦ p.formula ]            -- relink in place
          out.formula := φ' ;  out
```

The accumulator idiom: seed an OK result crediting `r`, credit each operand's
re-presentation, relink each, finish with the rewritten formula.

### Operand-wise relink (no node rebuild)

The operands of one node are **siblings** — pairwise incomparable, an antichain — so
relinking `ψᵢ → ψᵢ'` leaves the other operands untouched: the substitutions are
independent and order-free, and `N` need not be rebuilt from them. (`roundtrip_decomp`
is thus a fold of single-node `roundtrip`s over `operands(N)`.)

### Faithfulness

`R` is a Rewriter, so each `R(success(ψ)) ≡ ψ` (or declines). By congruence, replacing
each operand with an ω-equivalent one preserves `L(φ)`. Driven with an
`identity`-floored `R` (`best_of(identity, …)`) no operand declines, so
`roundtrip_decomp` never declines and never regresses; it returns `r` unchanged when
`Φ` declines.

## The climb

Tie `R` to `roundtrip_decomp` itself (via `recurse`): each operand is decomposed before
it is relinked, so the re-derivation compounds bottom-up — an ancestor is re-presented
from already-simplified descendants. The flat version is
`R = best_of(identity, relabel(Λ))`; the climb is the same construction with `R` the
recursion.
