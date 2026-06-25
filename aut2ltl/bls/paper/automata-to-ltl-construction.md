# Automata → LTL: Core Construction (Implementation Reference)

Based on **U. Boker, K. Lehtinen, S. Sickert, *On the Translation of Automata to Linear Temporal Logic*, FoSSaCS 2022 (full version)**.

This document is a self-contained reference for the **central construction**: translating a
**counter-free deterministic ω-regular automaton** into an equivalent LTL (future-only) formula,
via a **reset-cascade (Krohn–Rhodes–Holonomy) decomposition** and a family of inductively defined
**reachability formulas**.

> **Out of scope here** (intentionally omitted): the unary-alphabet section (Sec. 3), and the
> depth/length complexity analysis (Sec. 4.3, Table 2, Lemma 6). What remains is everything needed
> to *build the formula*: the definitions, the five reachability formulas, the acceptance-condition
> encoding, and a worked example.

---

## 0. The pipeline at a glance

```
counter-free deterministic ω-automaton  D   (Büchi / coBüchi / Muller / Rabin / weak / looping)
        │   every det. ω-automaton ≡ a Muller automaton over the same semiautomaton
        ▼
Krohn–Rhodes–Holonomy decomposition (Prop. 6, 7, 8)
        │   produces a RESET CASCADE  A  homomorphic to D's semiautomaton,
        │   with the acceptance condition lifted to A's CONFIGURATIONS
        ▼
reachability formulas  (Sec. 4.2)  — the technical core of this paper
        │   reach / wreach / solid / wsolid / dashed, defined by induction on cascade LEVEL
        ▼
acceptance encoding  (Sec. 4.4)  — Fin(C) + per-acceptance-condition Boolean combination
        ▼
equivalent LTL formula  φ   (in the matching class of the syntactic future hierarchy)
```

**Key guarantee (Theorem 2).** If `D` is looping-Büchi / looping-coBüchi / weak / Büchi / coBüchi /
Muller, then `φ` lands in `Π₁ / Σ₁ / Δ₁ / Π₂ / Σ₂ / Δ₂` respectively (the matching syntactic
fragment). In particular a safety automaton yields a *syntactic safety* formula.

---

## 1. LTL (future-only): syntax, semantics, measures

Atomic propositions `AP`. Alphabet `Σ = 2^AP`. A **letter** `σ ∈ Σ` is a subset of `AP`.
Formulas are built from:

```
true | a (a ∈ AP) | ¬φ | φ ∧ ψ | X φ | φ U ψ
```

Semantics over a finite or infinite word `w ∈ Σ⁺ ∪ Σ^ω` (`w[i]` = i-th letter, `w[i..]` = suffix
from `i`, `|w|` = length, `∞` if infinite):

```
w ⊨ true
w ⊨ a          iff  a ∈ w[0]
w ⊨ ¬φ         iff  w ⊭ φ
w ⊨ φ ∧ ψ      iff  w ⊨ φ and w ⊨ ψ
w ⊨ X φ        iff  |w| > 1 and w[1..] ⊨ φ
w ⊨ φ U ψ      iff  ∃ i ∈ [0..|w|).  w[i..] ⊨ ψ  and  ∀ j ∈ [0..i). w[j..] ⊨ φ
```

Derived: `false := ¬true`, `φ ∨ ψ := ¬(¬φ ∧ ¬ψ)`, `F φ := true U φ`, `G φ := ¬F¬φ`,
`ψ₁ R ψ₂ := ¬((¬ψ₁) U (¬ψ₂))` (release / weak-until dual).

**Over infinite words** `X` is self-dual: `¬X ψ ≡ X¬ψ`, so `X true ≡ true` and `X false ≡ false`.
(This *fails* on finite words of length 1 — see §10.)

**Measures.** `|φ|` = number of syntax-tree nodes (length); *size* = nodes of the DAG of the tree
(sharing common subformulas); temporal nesting depth:

```
depth(true)=depth(a)=0
depth(¬ψ)=depth(ψ)
depth(ψ₁∧ψ₂)=max(depth ψ₁, depth ψ₂)
depth(Xψ)=depth(ψ)+1
depth(ψ₁ U ψ₂)=max(depth ψ₁, depth ψ₂)+1
```

---

## 2. Syntactic future hierarchy (Σᵢ, Πᵢ, Δᵢ)

These classes are *syntactic* fragments; the construction places its output formulas into them.

```
Σ₀ = Π₀ = Δ₀ : least set containing all atomic props and their negations,
              closed under ∧, ∨.

Σ_{i+1} : least set containing  Π_i  and negations of Π_{i+1},
          closed under ∧, ∨, X, U.

Π_{i+1} : least set containing  Σ_i  and negations of Σ_{i+1},
          closed under ∧, ∨, X, R.

Δ_{i+1} : least set containing Σ_{i+1} and Π_{i+1},
          closed under ∧, ∨, ¬.
```

- `Σ₁` = **syntactic co-safety** (guarantee), `Π₁` = **syntactic safety**.
- `¬` maps `Σᵢ ↔ Πᵢ`. `Σᵢ` is closed under `U`; `Πᵢ` under `R`.

| det. automaton class | language class | LTL fragment |
|---|---|---|
| looping-Büchi   | safety        | `Π₁` |
| looping-coBüchi | guarantee/co-safety | `Σ₁` |
| weak            | obligation    | `Δ₁` |
| Büchi           | recurrence    | `Π₂` |
| coBüchi         | persistence   | `Σ₂` |
| Rabin / Muller  | reactivity    | `Δ₂` |

---

## 3. Automata

**Deterministic semiautomaton** `(Σ, Q, δ)`, `δ : Q×Σ → Q`, extended to words as usual.
`δ(q, w)` = state reached from `q` after reading finite word `w`.

**Reset semiautomaton.** For every letter `σ`, *either*
(i) `δ(q,σ)=q` for all `q` (σ acts as **identity**), *or*
(ii) there is `q'` with `δ(q,σ)=q'` for all `q` (σ acts as a **reset to `q'`**).

**Counter-free semiautomaton.** For every state `q`, word `u ∈ Σ⁺`, `n ≥ 1`:
`q` has a self-loop on `uⁿ` iff `q` has a self-loop on `u`. (No nontrivial cycles / "counting".)
Counter-free = LTL/FO/star-free definable.

**Deterministic automaton** `(Σ, Q, ι, δ, α)`: semiautomaton + initial `ι` + acceptance `α`.

**Acceptance conditions** (for ω-words; `inf(r)` = states visited infinitely often by run `r`):

- **Muller** `α = {M₁,…,M_k}`, `Mᵢ ⊆ Q`: accept iff `inf(r) = Mᵢ` for some `i`.
- **Rabin** `α = {(G₁,B₁),…,(G_k,B_k)}`: accept iff `∃i. Gᵢ∩inf(r)≠∅ ∧ Bᵢ∩inf(r)=∅`.
- **Büchi** `α ⊆ Q`: accept iff `α ∩ inf(r) ≠ ∅`.
- **coBüchi** `α ⊆ Q`: accept iff `α ∩ inf(r) = ∅`.
- **weak** = Büchi where every SCC is entirely in `α` or entirely out of `α`.
- **looping** = Büchi or coBüchi where *all* states are in `α` except a single sink state.

Every deterministic ω-regular automaton is equivalent to a deterministic **Muller** automaton on the
**same** semiautomaton — this is the entry point for the construction (you only ever need to handle a
Muller condition, plus shortcuts for the simpler classes).

---

## 4. Cascades (reset-cascade decomposition)

### 4.1 Cascaded semiautomaton

A **cascade** over `Σ` with `n` levels is `A = ⟨Σ, A₁, …, Aₙ⟩` where each level is a semiautomaton

```
Aᵢ = (Σᵢ, Qᵢ, δᵢ),     Σᵢ = Σ × Q₁ × … × Q_{i-1}
```

So level `i` reads the real letter **together with the current states of all lower levels**.
`Σ₁ = Σ`, `Σ₂ = Σ×Q₁`, etc. A **combined letter** at level `i` is a pair `⟨σ, S⟩` with `σ ∈ Σ` and
`S` an `(i−1)`-configuration.

`A` is a **reset cascade** iff every `Aᵢ` is a reset semiautomaton. (We only translate reset
cascades.)

**Configurations.** An `i`-configuration is a tuple `S = ⟨q₁,…,qᵢ⟩ ∈ Q₁×…×Qᵢ`.
We write `⟨S, q_{i+1}⟩` for the `(i+1)`-configuration extending `S`. The unique 0-configuration is the
empty tuple `⟨⟩`. "Configuration" with no qualifier = `n`-configuration.

**Transition on configurations** (pointwise; lower levels feed higher levels):

```
δ_{≤i}(⟨q₁,…,qᵢ⟩, σ) = ⟨ δ₁(q₁, ⟨σ⟩),
                          δ₂(q₂, ⟨σ, q₁⟩),
                          δ₃(q₃, ⟨σ, q₁, q₂⟩),
                          … ⟩
```

We drop the `≤i` subscript when clear, and write `δ(S, w)` for the configuration reached after a
finite word `w`.

**Induced semiautomaton `D_A`.** Its states are the `n`-configurations of `A`, transition `δ_{≤n}`.
With up to `j` states per level there are up to `jⁿ` configurations.
(Normalization: a reset cascade can be rewritten with `≤ n·log j` levels and **2 states per level**
— useful for implementation since it makes Enter/Stay/Leave trivial per level.)

### 4.2 Enter / Stay / Leave (the per-level letter classification)

For a state `q ∈ Qᵢ` of level `i`, define three sets of **combined letters** in
`Σ × Q₁ × … × Q_{i-1}`:

```
Enter(q) = combined letters that RESET level-i state to q   (from any state → q)
Stay(q)  = combined letters that keep level-i state at q     (identity letters + resets to q)
Leave(q) = combined letters that move level-i state OFF q    (resets to some q' ≠ q)
```

Facts (from the reset property): `Enter(q) ⊆ Stay(q)`, and `Leave(q)` is the complement of
`Stay(q)` (w.r.t. the relevant combined letters). Identity letters are in `Stay` but **not** in
`Enter`.

These three sets are *the* primitives the reachability formulas branch over.

### 4.3 Homomorphism and the decomposition theorems

A semiautomaton `(Σ, Q, δ)` is **homomorphic** to a cascade `⟨Σ, A₁,…,Aₙ⟩` if there is a partial
surjective `φ : Q₁×…×Qₙ → Q` with, for all `σ ∈ Σ`, `S`:

```
δ(φ(S), σ) = φ(δ_{≤n}(S, σ))
```

**Prop. 6 (Krohn–Rhodes–Holonomy, the cascade you feed the construction).**
Every counter-free deterministic semiautomaton with `n` states is homomorphic to a **reset cascade**
with up to `2ⁿ` levels and up to `2n` states per level.

**Prop. 7 (acceptance lifts: Büchi / coBüchi / Rabin).**
If `D` is a deterministic Büchi / coBüchi / Rabin automaton whose semiautomaton is homomorphic to
cascade `A`, there is an equivalent automaton `D'` of the same kind **whose semiautomaton is `A`**
(Rabin keeps the same number of pairs). Concretely, lift each accepting/rejecting state-set
`G ⊆ Q` to `G' = h⁻¹(G)` over configurations.

**Prop. 8 (acceptance lifts: Muller).**
If `D` is a Muller automaton with `n` states homomorphic to a reset cascade `A` with `m`
configurations, there is an equivalent Muller automaton `D'` on `A` whose condition has up to
`2^{O(mn)}` acceptance sets. (Each Muller set `M = {q₁,…,q_l}` becomes the family of config-sets
`G` with `h(G)=M`, i.e. pick `≥1` configuration from each `h⁻¹(qᵢ)`.)

> **Implementation takeaway.** The reachability machinery below assumes its input is a **reset
> cascade `A` together with an acceptance condition expressed over the configurations of `A`** and an
> initial configuration `ι`. Props. 6–8 are exactly what produces that input.

---

## 5. Notation for the reachability formulas

The heart of the paper is one parameterised LTL formula and four auxiliaries, all written in the
paper with decorated arrows. This reference uses **named functions** (greppable, unambiguous) and
gives the paper-arrow next to each.

| name (here) | paper arrow | meaning (informal) | arrow style |
|---|---|---|---|
| `reach(S,B,β,T,τ)`  | `S ↝[B(β)] T(τ)`              | **strong** reach `T` (suffix ⊨ τ) **without** hitting bad `B` (suffix ⊨ β) | squiggly |
| `wreach(S,B,β,T,τ)` | `S ↝ʷ[B(β)] T(τ)`             | **weak** dual of `reach` (release) | squiggly, weak |
| `solid(⟨S,s⟩,⟨B,b⟩,β,⟨T,t⟩,τ)`  | `⟨S,s⟩ →[⟨B,b⟩(β)] ⟨T,t⟩(τ)`  | reach **while the top-level state stays `s`** (forces `t = s`) | solid |
| `wsolid(⟨S,s⟩,⟨B,b⟩,β,⟨T,t⟩,τ)` | `⟨S,s⟩ →ʷ[⟨B,b⟩(β)] ⟨T,t⟩(τ)` | weak version of `solid` | solid, weak |
| `dashed(⟨S,s⟩,⟨B,b⟩,β,⟨T,t⟩,τ)` | `⟨S,s⟩ ⇢[⟨B,b⟩(β)] ⟨T,t⟩(τ)`  | reach **while the top-level state changes `s ⤳ t`** (`s ≠ t`) | dashed |

Conventions used throughout:

- `S`, `B`, `T` are configurations of the **same level**; `s`, `b`, `t` are the **next-level** states;
  `⟨S,s⟩` denotes a level-`(m+1)` configuration with lower part `S` (level `m`) and top state `s`.
- `β` (the "bad" suffix obligation) and `τ` (the "target" suffix obligation) are arbitrary LTL formulas.
- `δ(⟨X, ·⟩, σ)`: the configuration reached by reading combined letter `⟨σ, X⟩` — the `·` marks that,
  in a reset cascade, the **lower successor does not depend on the dropped top-level state**
  (`δ(⟨X,q⟩,σ) = δ(⟨X,p⟩,σ)` for all `p, q`), so it can be omitted.
- `⋁`/`⋀` over an empty index set are `false`/`true` respectively.

The two big modes:

```
solid : the run STAYS in the top-level state s (so necessarily t = s).
        Recurses to reach/wreach at the LOWER level (drop s), branching over Stay(s), Leave(s).
dashed: the run LEAVES s and ENTERS t (s ≠ t).
        Branches over Enter(t), Enter(b), Leave(s); reuses solid/wsolid at the SAME level inside X(…).
```

---

## 6. Intended semantics (formal — this is Table 1)

Each formula is *correct* exactly when the equivalence below holds (`δ(·,·)` on configurations,
`w` infinite). These are the specs to test an implementation against.

**(1) `reach(S,B,β,T,τ)`** — *not reaching `B(β)` until reaching `T(τ)`*:

```
w ⊨ reach(S,B,β,T,τ)  ⟺
  ∃ i ≥ 0.  δ(S, w[0..i)) = T  ∧  w[i..] ⊨ τ
           ∧ ∀ j ∈ [0..i).  ( δ(S, w[0..j)) ≠ B  ∨  w[j..] ⊭ β )
```

**(2) `wreach(S,B,β,T,τ)`** — *reaching `T(τ)` releases not reaching `B(β)`*:

```
w ⊨ wreach(S,B,β,T,τ)  ⟺
  ∀ i ≥ 0.  ( δ(S, w[0..i)) = B  ∧  w[i..] ⊨ β )
            → ( ∃ j ∈ [0..i).  δ(S, w[0..j)) = T  ∧  w[j..] ⊨ τ )
```

**(3) `solid(⟨S,s⟩,⟨B,b⟩,β,⟨T,t⟩,τ)`** — *(1) while always staying in top state `s`*:

```
w ⊨ solid(…)  ⟺
  ∃ i ≥ 0.  δ(⟨S,s⟩, w[0..i)) = ⟨T,t⟩  ∧  w[i..] ⊨ τ
           ∧ ∀ j ∈ [0..i). ( δ(⟨S,s⟩, w[0..j)) ≠ ⟨B,b⟩  ∨  w[j..] ⊭ β )
           ∧ ∀ j ∈ [0..i). ⟨ w[j], δ(S, w[0..j)) ⟩ ∈ Stay(s)
```

**(4) `wsolid(⟨S,s⟩,⟨B,b⟩,β,⟨T,t⟩,τ)`** — *reaching `⟨T,t⟩(τ)` releases not (reaching `⟨B,b⟩(β)` or leaving `s`)*:

```
w ⊨ wsolid(…)  ⟺
  ∀ i ≥ 0.  [ ( δ(⟨S,s⟩, w[0..i)) = ⟨B,b⟩ ∧ w[i..] ⊨ β )
            ∨ ( i > 0 ∧ ⟨ w[i-1], δ(S, w[0..i-1)) ⟩ ∈ Leave(s) ) ]
            → ( ∃ j ∈ [0..i).  δ(⟨S,s⟩, w[0..j)) = ⟨T,t⟩ ∧ w[j..] ⊨ τ )
```

**(5) `dashed(⟨S,s⟩,⟨B,b⟩,β,⟨T,t⟩,τ)`** — *(1) while the top state changes (must `Enter(t)`, then `Leave(s)`)*:

```
w ⊨ dashed(…)  ⟺
  ∃ i₁, i₂ ≥ 0.  δ(⟨S,s⟩, w[0..i₁)) = ⟨T,t⟩  ∧  w[i₁..] ⊨ τ
              ∧ ( ∃ j₁ ∈ [0..i₁).  ⟨ w[j₁], δ(S, w[0..j₁)) ⟩ ∈ Enter(t) )
              ∧ ⟨ w[i₂], δ(S, w[0..i₂)) ⟩ ∈ Leave(s)
              ∧ ∀ j₂ ∈ [0.. max(i₁-1, i₂)].
                   ( δ(⟨S,s⟩, w[0..j₂)) ≠ ⟨B,b⟩  ∨  w[j₂..] ⊭ β )
```

**Class membership of the parameters (used pervasively).** When `reach`/`wreach` etc. appear, the
"avoid" obligation `β` is the *unwanted* side and the "target" obligation `τ` is the *wanted* side.
The construction picks `β`, `τ` so that (see Lemma 5):
`reach`, `solid`, `dashed` come out **co-safety (Σᵢ)**, and `wreach`, `wsolid` come out
**safety (Πᵢ)**.

---

## 7. The five reachability formulas (definitions)

Defined by **induction on the configuration level**. Mutual-recursion dependency (well-founded
because 3/4/5 always recurse into level `m` from level `m+1`):

```
reach   →  solid, dashed                 (same level)
wreach  →  reach                         (dual, same level)
solid   →  reach        at LOWER level
wsolid  →  wreach       at LOWER level
dashed  →  reach        at LOWER level,  and  solid / wsolid  at SAME level (inside X(…))
```

### Formula 1 — `reach` (main, strong)

```
reach(S, B, β, T, τ) :=
  ┌ (¬β) U τ                                            if S = ⟨⟩            (level 0, base case)
  └ solid(⟨S₀,s⟩, ⟨B₀,b⟩, β, ⟨T₀,t⟩, τ)
        ∨ dashed(⟨S₀,s⟩, ⟨B₀,b⟩, β, ⟨T₀,t⟩, τ)          otherwise
                                          where S=⟨S₀,s⟩, B=⟨B₀,b⟩, T=⟨T₀,t⟩
```

(The two disjuncts split on whether the top-level state is unchanged or changed.)

### Formula 2 — `wreach` (weak / release dual)

```
wreach(S, B, β, T, τ) := ¬ reach(S, T, τ, B, β)        -- note the (B,β) ↔ (T,τ) SWAP
```

### Formula 3 — `solid` (top state stays `s`; forces `t = s`)

Four cases on whether the **source** equals the **bad** and/or the **target** configuration:

```
solid(⟨S,s⟩, ⟨B,b⟩, β, ⟨T,t⟩, τ) :=
  ┌ P                       if ⟨S,s⟩≠⟨B,b⟩ and ⟨S,s⟩≠⟨T,t⟩
  │ P ∨ τ                   if ⟨S,s⟩≠⟨B,b⟩ and ⟨S,s⟩=⟨T,t⟩
  │ P ∧ ¬β                  if ⟨S,s⟩=⟨B,b⟩ and ⟨S,s⟩≠⟨T,t⟩
  └ (P ∧ ¬β) ∨ τ            if ⟨S,s⟩=⟨B,b⟩ and ⟨S,s⟩=⟨T,t⟩

where  P = solid⁺(⟨S,s⟩, ⟨B,b⟩, β, ⟨T,t⟩, τ)         (the ">0" / nonempty-prefix core)

solid⁺(⟨S,s⟩, ⟨B,b⟩, β, ⟨T,t⟩, τ) :=
  ⋁  over ⟨σ,T'⟩ ∈ Stay(s) such that δ(⟨T',s⟩, σ) = ⟨T,t⟩ :
     (
         reach(S, S, false, T', σ ∧ Xτ)                          -- reach T' (no real bad: β=false)
       ∧ ⋀ over ⟨η,L⟩ ∈ Leave(s) :                               -- never take a "leave s" letter first
             reach(S, L, η, T', σ ∧ Xτ)
       ∧ ⋀ over ⟨ρ,B'⟩ ∈ Stay(s) such that δ(⟨B',s⟩, ρ) = ⟨B,b⟩ : -- never hit bad ⟨B,b⟩ first
             reach(S, B', ρ ∧ Xβ, T', σ ∧ Xτ)
     )
```

Reading `solid⁺`: pick the **last** combined letter `⟨σ,T'⟩` (it stays in `s` and lands the lower
config in `T'`, then steps to `⟨T,t⟩=⟨T,s⟩`). At the **lower level**, reach `T'` with continuation
`σ ∧ Xτ`, while (a) never taking a `Leave(s)` letter beforehand and (b) never reaching the bad
configuration beforehand. The bad-config check is pushed one step back: a step into `⟨B,b⟩` happens by
reading some `⟨ρ,B'⟩ ∈ Stay(s)` from `B'` with `δ(⟨B',s⟩,ρ)=⟨B,b⟩`, and the suffix obligation `β`
becomes `ρ ∧ Xβ`.

### Formula 4 — `wsolid` (weak version of `solid`)

Same four-case shape but **note the 4th case differs** from Formula 3:

```
wsolid(⟨S,s⟩, ⟨B,b⟩, β, ⟨T,t⟩, τ) :=
  ┌ Q                       if ⟨S,s⟩≠⟨B,b⟩ and ⟨S,s⟩≠⟨T,t⟩
  │ Q ∨ τ                   if ⟨S,s⟩≠⟨B,b⟩ and ⟨S,s⟩=⟨T,t⟩
  │ Q ∧ ¬β                  if ⟨S,s⟩=⟨B,b⟩ and ⟨S,s⟩≠⟨T,t⟩
  └ (Q ∨ τ) ∧ ¬β            if ⟨S,s⟩=⟨B,b⟩ and ⟨S,s⟩=⟨T,t⟩      ←  differs from solid's "(P ∧ ¬β) ∨ τ"

where  Q = wsolid⁺(⟨S,s⟩, ⟨B,b⟩, β, ⟨T,t⟩, τ)

wsolid⁺(⟨S,s⟩, ⟨B,b⟩, β, ⟨T,t⟩, τ) :=
  -- line (1): eventually reach ⟨T,t⟩, still staying in s
  ⋁ over ⟨σ,T'⟩ ∈ Stay(s) such that δ(⟨T',s⟩, σ) = ⟨T,t⟩ :
     (
         ⋀ over ⟨η,L⟩ ∈ Leave(s) :              wreach(S, L, η, T', σ ∧ Xτ)
       ∧ ⋀ over ⟨ρ,B'⟩ ∈ Stay(s), δ(⟨B',s⟩,ρ)=⟨B,b⟩ : wreach(S, B', ρ ∧ Xβ, T', σ ∧ Xτ)
     )
  ∨
  -- line (2): never reach ⟨T,t⟩; just stay in s forever, never hitting bad and never leaving
     (
         ⋀ over ⟨η,L⟩ ∈ Leave(s) :              wreach(S, L, η, S, false)
       ∧ ⋀ over ⟨ρ,B'⟩ ∈ Stay(s), δ(⟨B',s⟩,ρ)=⟨B,b⟩ : wreach(S, B', ρ ∧ Xβ, S, false)
     )
```

Note: line (1) is `solid⁺` with `reach`→`wreach` and **without** the
`reach(S,S,false,T',…)` conjunct that *forced* reaching `T'` (weak ⇒ reaching is optional).
Line (2) uses target `⟨S, false⟩`: since `false` is never satisfiable, `wreach(S, X, ξ, S, false)`
means "**never** reach `X` with `ξ`" — i.e. never leave `s` and never hit bad, ad infinitum.

### Formula 5 — `dashed` (top state changes `s ⤳ t`, `s ≠ t`)

The hardest formula. Intuition: before reaching `⟨T,t⟩`, the run reads a letter `⟨σ,T'⟩ ∈ Enter(t)`
that switches the top state to `t`; from there it stays in `t` (via `solid`) and reaches `⟨T,t⟩`
while avoiding `⟨B,b⟩(β)`. It must also (line 3) actually leave `s`.

```
dashed(⟨S,s⟩, ⟨B,b⟩, β, ⟨T,t⟩, τ) :=

  ⋁ over ⟨σ,T'⟩ ∈ Enter(t) :
     (
       -- line (1): reach T' (no bad), then on σ enter t and stay-reach ⟨T,t⟩
       reach( S, S, false, T',
              σ ∧ X( solid( δ(⟨T',·⟩, σ), ⟨B,b⟩, β, ⟨T,t⟩, τ ) ) )

       ∧
       -- line (2): same, but ALSO avoid the bad top-state b on the way to T'
       ⋀ over ⟨η,R⟩ ∈ Enter(b) :
          reach( S,
                 R,  η ∧ X( wsolid( δ(⟨R,·⟩, η), ⟨T,t⟩, τ, ⟨B,b⟩, β ) ),   -- ← bad/target SWAPPED here
                 T',
                 σ ∧ X( solid( δ(⟨T',·⟩, σ), ⟨B,b⟩, β, ⟨T,t⟩, τ ) ) )
     )

  ∧
  -- line (3): the run really must leave s (read some Leave(s) letter, while having stayed & avoided bad)
  ⋁ over ⟨σ,L⟩ ∈ Leave(s) :
     solid( ⟨S,s⟩, ⟨B,b⟩, β, ⟨L,s⟩,
            σ ∧ ( ¬β  if ⟨L,s⟩ = ⟨B,b⟩ ;  true  otherwise ) )
```

Notes on Formula 5:

- `δ(⟨T',·⟩, σ)` is the configuration after the entering letter `⟨σ,T'⟩` (top state becomes `t`);
  `δ(⟨R,·⟩, η)` likewise after `⟨η,R⟩` (top becomes `b`). The dropped `·` is justified by reset
  cascades' lower-successor independence.
- Line (1) is needed for the corner case where `Enter(b)` is empty (then line (2) is vacuously `true`).
- Line (2) uses **`wsolid` with `⟨B,b⟩` and `⟨T,t⟩` swapped** (`wsolid(start, ⟨T,t⟩, τ, ⟨B,b⟩, β)`):
  it asserts that after entering `b`, you do **not** reach `⟨B,b⟩(β)` before reaching `⟨T,t⟩(τ)`.
  `wsolid` (not `solid`) is used here specifically so that `dashed` stays a **co-safety (Σᵢ)** formula.

---

## 8. Correctness and hierarchy

**Lemma 4 (correctness).** For all infinite `w ∈ (2^AP)^ω`, configurations `S,B,T` of level `m ≤ n`,
states `s,b,t` of level `m+1` (when `m < n`), and LTL formulas `β, τ`: the five definitions in §7
satisfy exactly the intended semantics in §6. (Proved by induction on level `m`; no circularity
because 2 builds on 1, 1 on {3,5}, and 3/4/5 recurse to a strictly lower level.)

**Lemma 5 (syntactic class).** For `i ≥ 1`:

```
if β ∈ Πᵢ and τ ∈ Σᵢ :   reach(S,B,β,T,τ),  solid(…),  dashed(…)   ∈ Σᵢ
if β ∈ Σᵢ and τ ∈ Πᵢ :   wreach(S,B,β,T,τ), wsolid(…)              ∈ Πᵢ
```

(Driver of the "matching fragment" guarantee in Theorem 2.)

---

## 9. From reachability to the acceptance condition

### 9.1 Shorthands

```
reach_to(S, T, τ)   :=  reach(S, T, false, T, τ)          -- "S ↝ T(τ)": reach T (suffix τ), no real bad
reach_to(S, T)      :=  reach_to(S, T, true)              -- "S ↝ T": just reach T (immediate if S=T)

reach_to⁺(S, T)     :=  ⋁ over σ ∈ Σ :                    -- "S >0↝ T": reach T after a NONEMPTY prefix
                            ( σ ∧ X( reach_to(δ(S,σ), T) ) )
```

### 9.2 Visiting a configuration finitely often (Lemma 7)

For a cascade `A = ⟨2^AP, A₁,…,Aₙ⟩`, initial configuration `ι`, and any configuration `C`:
the run of `A` on `w` (from `ι`) visits `C` **finitely often** iff `w ⊨ Fin(C)`, where

```
Fin(C) := ¬ reach_to(ι, C)                       -- C is never visited at all
        ∨ reach_to( ι, C, ¬ reach_to⁺(C, C) )    -- OR there is a LAST visit to C (after it, C is never re-entered)
```

Furthermore `Fin(C) ∈ Σ₂` (so `¬Fin(C) ∈ Π₂`). These are the only "atoms" you need to express any
ω-regular acceptance condition over the cascade's configurations.

### 9.3 Theorem 2 — building φ per acceptance condition

Let the cascade `A` (configurations `Cfg`, initial `ι`) carry the acceptance condition lifted from
`D` (Props. 7/8). Build `φ` from `Fin(C)`:

**Muller** (the general case; `α = {M₁,…,M_k}`, each `Mⱼ` a set of *configurations* to be the exact
inf-set):

```
φ := ⋁ over each Muller config-set G ∈ α :
        ( ⋀ over C ∈ G   : ¬Fin(C) )      -- every config in G visited infinitely often
      ∧ ( ⋀ over C ∉ G   :  Fin(C) )      -- every other config visited finitely often
```

`φ` is a Boolean combination of `Σ₂` formulas ⇒ `φ ∈ Δ₂`. (This is where the size blow-up lives:
there can be up to `2^{O(mn)}` Muller sets, each ranging over up to `mᵐ` configurations.)

**coBüchi** (`α` = configs that must be visited finitely often):

```
φ := ⋀ over C mapped to a state in α :  Fin(C)            -- φ ∈ Σ₂
```

**Büchi** (`α` = configs visited infinitely often) — negate the coBüchi of the complement:

```
φ := ⋁ over C mapped to a state in α :  ¬Fin(C)           -- φ ∈ Π₂
```

**looping-coBüchi** (accepting ⇔ eventually reach the unique sink; `S_sink` = configs mapped to the
sink state):

```
φ := ⋁ over C ∈ S_sink :  reach_to(ι, C)                  -- φ ∈ Σ₁  (guarantee / co-safety)
```

**looping-Büchi** (dual: accepting ⇔ **never** reach the sink):

```
φ := ⋀ over C ∈ S_sink :  ¬ reach_to(ι, C)               -- φ ∈ Π₁  (safety)
```

**weak** (accept ⇔ the run eventually settles in some accepting SCC). For each accepting SCC `G ⊆ Q`,
let `G'` = states reachable from `G` but not in `G`; let `H = h⁻¹(G)`, `H' = h⁻¹(G')` be the
corresponding config-sets. "End up in `G`" is captured by:

```
end_in(G) :=  ( ⋁ over C ∈ H   :   reach_to(ι, C) )
            ∧ ( ⋀ over C' ∈ H'  : ¬ reach_to(ι, C') )

φ := ⋁ over each accepting SCC G :  end_in(G)             -- φ ∈ Δ₁  (obligation)
```

**Corollary 1.** Every counter-free deterministic ω-regular automaton (any acceptance condition)
recognises an LTL-definable language (route through the equivalent Muller automaton + Theorem 2).

**Corollary 2 (looping).** A deterministic looping-Büchi (looping-coBüchi) automaton with `n` states
recognising an LTL-definable language is equivalent to a `Π₁` (`Σ₁`) formula. (Uses Prop. 9: such an
automaton can first be made counter-free with `≤ n` states.) This gives an *elementary* bound for the
liveness–safety decomposition and for turning semantic-safety LTL into syntactic-safety LTL.

---

## 10. Finite-word adaptation (Remark 2)

Theorem 2 adapts to finite words with **one** structural change. On infinite words `X` is self-dual;
on finite words it is not (they differ on words of length 1), so a **weak next** is needed:

```
X̃ ψ := ¬X¬ψ            -- "weak next": holds at the last position; agrees with X except on length-1 words
```

Finite-word syntactic co-safety (safety) is built from `true,false,a,¬a,∨,∧` and `U, X` (resp.
`R, X̃`). The only change to the translation: **replace some `X` with `X̃` in Formula 4 (`wsolid`)**.
A double-exponential-*size* counter-free-DFA→LTL translation already existed (Wilke), but it does not
guarantee syntactic safety/co-safety output the way this construction does.

---

## 11. Worked example

A small **single-level** reset cascade, to exercise the base case, `Enter/Stay/Leave`, and the
`solid`/`dashed`/`Fin` machinery end-to-end.

### Setup

`Σ = {a, b}` (two letters), one level, `Q₁ = {p, q}`:

```
letter a : reset everyone to q     (δ₁(p,a)=q, δ₁(q,a)=q)
letter b : identity                (δ₁(p,b)=p, δ₁(q,b)=q)
```

Since there is only one level, combined letters are just the real letters (no lower config). The
induced automaton has states `{p, q}`: from `p`, read `b` → stay `p`, read `a` → go to `q`; `q` is a
sink (`Leave(q)=∅`). Take `ι = p`.

`Enter/Stay/Leave` (over `Σ`):

```
Enter(p) = ∅          Stay(p) = {b}          Leave(p) = {a}
Enter(q) = {a}        Stay(q) = {a, b}       Leave(q) = ∅
```

(`a` resets to `q` ⇒ `a ∈ Enter(q)`; `b` is identity ⇒ in `Stay` but not in `Enter`.)

### Base case

At level 1, a configuration's lower part is `⟨⟩`, so every `solid`/`dashed` recurses into the
**level-0 base case**:

```
reach(⟨⟩, ⟨⟩, β, ⟨⟩, τ) = (¬β) U τ
```

### Compute `reach_to(p, q) = reach(p, q, false, q, true)` (i.e. "reach the sink q from p")

Top states: start `s = p`, target `t = q`. Since `s ≠ t`, `solid` is vacuous (it would force `t=s`)
and the work is in `dashed`. Unfolding (using `X true ≡ true`, `X false ≡ false`, and the base case
`reach(⟨⟩,⟨⟩,β,⟨⟩,τ)=(¬β)Uτ`):

```
-- dashed lines (1)&(2), over Enter(q)={a}, give (after solid(q,q,false,q,true)=true): 
       F a
-- dashed line (3), over Leave(p)={a}, gives:
       solid(p, q, false, p, a)
     = solid⁺(p,q,false,p,a) ∨ a                      (case ⟨S,s⟩≠⟨B,b⟩, ⟨S,s⟩=⟨T,t⟩ ⇒ "P ∨ τ")
     = [ F(b ∧ X a)  ∧  (¬a) U (b ∧ X a) ]  ∨  a
     ≡ ( (¬a) U (b ∧ X a) ) ∨ a
```

So:

```
reach_to(p, q)  ≡  F a  ∧  ( ((¬a) U (b ∧ X a)) ∨ a )   ≡   F a
```

which is correct: from `p` you reach the sink `q` exactly when an `a` is eventually read (`F a`).
The construction produces an *unsimplified but equivalent* `F a`; the line-(1)&(2) part encodes
"enter `q` then stay", the line-(3) part encodes "leave `p`".

### Acceptance: "eventually reach `q`" as a guarantee property

Treat the cascade as **looping-coBüchi** with sink set `S_sink = {q}` (accepting ⇔ eventually reach
the sink). Then by §9.3:

```
φ := ⋁ over C ∈ {q} :  reach_to(ι, C)  =  reach_to(p, q)  ≡  F a            ∈ Σ₁
```

a syntactic **co-safety** (`Σ₁`) formula, as the hierarchy table predicts for a guarantee language.

> The example deliberately collapses (single level, trivial lower part). On multi-level cascades the
> `solid⁺`/`dashed` recursion nests: each level wraps the previous one's reach-formulas as the `β`/`τ`
> parameters inside `σ ∧ Xτ` / `ρ ∧ Xβ`, which is the source of the depth/length growth (omitted here).

---

## 12. Implementation notes & pitfalls

1. **Recursion is on cascade level.** Memoise per `(formula-id, level, S, B, T, β, τ)`. Within a
   level, `reach → solid/dashed` and `dashed → solid/wsolid` are same-level, but every `solid`/
   `wsolid`/`dashed` ultimately recurses into `reach`/`wreach` at level `m-1`, so it terminates.

2. **The `(B,β) ↔ (T,τ)` swaps are easy to get wrong.** They appear in exactly two places:
   `wreach(S,B,β,T,τ) = ¬reach(S, T, τ, B, β)`, and in `dashed` line (2)'s inner
   `wsolid(…, ⟨T,t⟩, τ, ⟨B,b⟩, β)`.

3. **`solid` vs `wsolid` 4th case differ:** `solid` ⇒ `(P ∧ ¬β) ∨ τ`; `wsolid` ⇒ `(Q ∨ τ) ∧ ¬β`.
   They are *not* duals of each other (both must independently enforce "stay in `s`").

4. **`Enter ⊆ Stay`, identity letters are in `Stay` not `Enter`, `Leave = complement of Stay`.**
   With the 2-states-per-level normalization, each level's `Enter/Stay/Leave` is tiny — strongly
   recommended for a first implementation.

5. **`δ(⟨X,·⟩,σ)` (the `·`)** relies on reset-cascade lower-successor independence; just compute the
   successor configuration of `⟨X, (anything)⟩` under `σ` and read off the new lower part / new top
   state.

6. **`X true ≡ true`, `X false ≡ false` only on infinite words.** If you target finite words, switch
   to the weak next `X̃` inside Formula 4 (`wsolid`) per §10, and keep the strong `X` elsewhere.

7. **Letter encoding.** Each `σ ∈ Σ = 2^AP` used as a leaf in the formula is the conjunction
   `⋀_{a∈σ} a ∧ ⋀_{a∉σ} ¬a`. Treated as length 1 in the paper's analysis, but its real length is
   `3·log₂|Σ|`; multiply through once at the end if you track size.

8. **Acceptance must already be over configurations.** Run Props. 7/8 first: lift each state-set in
   `D`'s condition to its `h⁻¹(·)` config-set on the cascade `A` before invoking `Fin(C)`.

9. **Prefer the simpler acceptance encodings when applicable** (looping/weak/Büchi/coBüchi) — the
   general Muller route multiplies out a disjunction over up to `2^{O(mn)}` config-sets and is the
   expensive path.

10. **Reference checks.** Validate an implementation against the §6 semantics directly: for small
    cascades, brute-force the LHS predicate over ultimately-periodic words `u·vᵒᵐᵉᵍᵃ` and compare to
    the model-check of the generated formula.

---

### Symbol quick-reference

```
⟨q₁,…,qᵢ⟩      i-configuration            ⟨S,s⟩  extend config S with top state s     ⟨⟩  empty config
δ(S, w)        config reached from S on finite word w
Enter(q)/Stay(q)/Leave(q)   combined-letter classes for level-i state q
reach   S ↝[B(β)] T(τ)        wreach  S ↝ʷ[B(β)] T(τ)
solid   ⟨S,s⟩ →[⟨B,b⟩(β)] ⟨T,t⟩(τ)        wsolid ⟨S,s⟩ →ʷ[⟨B,b⟩(β)] ⟨T,t⟩(τ)
dashed  ⟨S,s⟩ ⇢[⟨B,b⟩(β)] ⟨T,t⟩(τ)
reach_to(S,T)  S ↝ T          reach_to⁺(S,T)  S >0↝ T          Fin(C)  C visited finitely often
Σᵢ co-safety/Π₁ safety/Δᵢ Boolean-closure        X̃ weak next (finite words only)
```
