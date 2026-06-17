# aut2ltl.inv — the invariant-layer Translator decorator

`Invariant(Λ)` wraps any `Translator` `Λ`: it factors a global safety invariant out
of the input language, delegates the *simplified* language to `Λ`, and re-asserts
the invariant on `Λ`'s result. It is defined entirely against the Translator
contract — it asks the input for one representation (its TGBA), calls `Λ` once, and
combines — and assumes nothing about what `Λ` is.

## The algorithm

### Setting

The only contract surface `inv` uses:

```
Label       =  Some φ  |  ⊥                 -- φ an LTL formula; ⊥ = decline
Translator  =  Language → Label             -- a Label also carries a technique tag
```

A `Language` offers a **TGBA** form `A = tgba(L) = (Q, Σ, δ, q0, F)` — edges
`(src, g, dst, A)` with a Boolean guard `g` (a BDD over `AP`) — and re-wraps a
concrete automaton back into a Language via `of(A)`. `inv` needs nothing more.

### The invariant

Abbreviate the disjunction of all of `A`'s edge guards:

```
Σ  =  ⋁ { g : (·, g, ·, ·) ∈ δ }
```

`Σ` is a **sound global safety invariant by construction**: every guard `g ⊨ Σ`,
so every letter any accepted word reads satisfies `Σ`, hence `G(Σ)` holds on all of
`L(A)`. Nothing has to be *checked* — `Σ` is invariant because it is the union of
the guards. It is also strictly **stronger** than any per-literal invariant: it
keeps the full Boolean, so guards `{a∧b, ¬a∧¬b}` — which force no single literal —
still yield `G(a ↔ b)`.

Reachability is a **quality** knob, not a correctness one: an unreachable edge's
guard only enlarges `Σ`, weakening `G(Σ)` and the strip below, never unsound. A
trimmed `A` sharpens the invariant; it is not required for soundness.

### The factorization (exact)

```
L(A)  =  L(strip(A, Σ))  ∩  L(G Σ)
```

exact in both directions: every accepted word is all-`Σ`-letters (⊆), and on
`Σ`-letters a stripped guard agrees with its original (⊇). The strip rewrites each
edge guard by the **Coudert–Madre restrict** under care-set `Σ`:

```
strip(A, Σ)  =  A with every guard  g ↦ simplify(g, Σ)
```

`simplify(g, Σ)` (BuDDy `bdd_simplify`) agrees with `g` wherever `Σ` holds and is
free — *don't-care* — on `¬Σ`, the letters no edge admits. Hence
`simplify(g, Σ) ∧ Σ ≡ g ∧ Σ`, exactly what the two inclusions need. The strip
removes from each guard precisely the part `G(Σ)` will carry globally, so `Λ` sees
**smaller guards** (and may newly land inside a fragment it can label).

### The decorator

```
inv(Λ) : Translator
inv(Λ)(L) =
    let A = tgba(L); Σ = ⋁ { g : (·,g,·,·) ∈ δ } in
    if Σ ≡ true then Λ(L)                          -- vacuous: pass through, NO credit
    else case Λ( of(strip(A, Σ)) ) of
           Some φ  →  Some( φ ∧ G(Σ) )             -- credit `inv`
           ⊥       →  ⊥                            -- propagate decline / verdict
```

Three cases:

- **Vacuous** (`Σ ≡ true` — the guards already cover `2^AP`): `G(true)` carries
  nothing, so delegate the *original* `L` to `Λ` and credit nothing. Not a decline:
  a decorator that declined here would discard a perfectly good `Λ` answer.
- **Non-vacuous, `Λ` succeeds**: return `φ ∧ G(Σ)` and add `inv` to the technique.
- **Non-vacuous, `Λ` declines** (`⊥`): carry the decline (status + diagnosis) out —
  `inv` only *strengthens* an OK result, never manufactures a formula.

The non-vacuous cases go through the result build/accumulate idiom — seed an
accumulator crediting `inv`, credit `Λ`'s result in, fill the formula only on OK —
so every field `Λ` carries (technique, diagnosis, future step-trace) flows through
the contract rather than being copied by hand.

The strip and the re-assertion of `G(Σ)` sit at the **same `Language` boundary,
around the same `Λ` call**: whatever is stripped is re-added at the same level, so
`Λ` always receives a self-consistent language and the factorization stays exact no
matter what `Λ` does with it.

### Idempotence

`inv` is naturally **idempotent** on most inputs: after one strip the residual
guards' disjunction tends to collapse toward `true` (e.g. `{a∧b, ¬a∧¬b} ↦ {a, ¬a}`,
whose `⋁` is `true`), so a second application is vacuous and self-credits nothing.

## Modules

- **`invariant.py`** — the `Invariant` decorator: the contract logic
  (Σ-vacuous pass-through, strip-and-delegate, re-assert `G(Σ)` + credit).
- **`strip.py`** — the BDD mechanics: `sigma(aut)` (`⋁` of all edge guards) and
  `strip(aut, care)` (per-edge Coudert–Madre restrict via `buddy.bdd_simplify`,
  preserving states / acceptance / APs).

## Layering

Imports `spot` / `buddy` and the contract floor (`aut2ltl.language`,
`aut2ltl.result`, `aut2ltl.contract`). Depends on no engine (`kr`, `sl`) and on no
composition layer; composites that place `inv` live above it.
