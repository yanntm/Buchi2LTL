# The roundtrip algorithm

A `Rewriter` that **re-presents one located node**. `roundtrip(R, Φ)` locates a node
`n = Φ(φ)` of the input formula, re-presents the subformula at `n` with the Rewriter
`R`, and relinks the result in place. It carries no seed — seeding (automaton →
formula) is `as_translator`'s, see `ltl_rewriter`.

## Setting

```
Rewriter  =  LTLResult → LTLResult
R         :  Rewriter               -- the node's re-presentation (e.g. relabel(Λ))
Φ         :  Formula → (Node | ⊥)   -- the node finder
```

A node `n` is a subformula occurrence, so `φ↓n = n`; `φ[n ↦ ψ]` substitutes by
hash-consed identity (`subst`).

## The construction

```
roundtrip(R, Φ) : Rewriter
roundtrip(R, Φ)(r) =
    let φ = r.formula; n = Φ(φ) in
    if n = ⊥ then r                              -- finder declines → identity (no self-credit)
    else case R( success(φ↓n) ) of
           ⊥        →  that decline              -- not masked
           Some p   →  start(tag).credit(r).credit(p)  with formula  φ[n ↦ p.formula]
```

## Faithfulness

`R` is a Rewriter, so `R(success(φ↓n)) ≡ φ↓n` (or declines). By congruence
(`w,i ⊨ φ ⇔ w[i:] ∈ L(φ)`), replacing `n` with an ω-equivalent subformula preserves
`L(φ)` under any context. A finder decline returns `r` unchanged; a declined
re-presentation propagates. Faithful-or-`⊥`.

## Relation to roundtrip_decomp

`roundtrip` re-presents the located node itself; `roundtrip_decomp` re-presents that
node's *operands*, and is a fold of `roundtrip` over them. With `R = relabel(Λ)` the
re-presentation is the language round trip; with `R = roundtrip_decomp` (tied via
`recurse`) the re-derivation compounds bottom-up.
