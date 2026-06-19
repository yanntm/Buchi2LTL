# The daisystar algorithm

A combinator translator that peels a **rejecting star** — the initial SCC of a
TGBA, presented as a hub with self-loop petals and one-hop spokes, when no run
that stays in the SCC forever is accepting — and emits the closed-form LTL of the
language accepted from it, delegating every exit target to a child translator. It
is a **local, context-free production**: it inspects one SCC's own edges and
treats each exit target's label as an opaque sub-term supplied by the child. It is
the *reachability* counterpart of `daisy2`: where that peels a recurrence star
(`STAY∞ ∨ LEAVE`), daisystar peels a star whose acceptance lies entirely past it,
so the language is pure `LEAVE`.

## Setting

A translator maps a language to a label; this one is parameterized by the child
`Λ` it delegates exit targets to:

```
Label       =  Some φ  |  ⊥                  -- φ an LTL formula; ⊥ = decline
Translator  =  Language → Label
```

daisystar asks the Language for its **TGBA** form `A = tgba(L)`,
`A = (Q, Σ, δ, q0, {F_1,…,F_m})`, `Σ = 2^AP`. An edge `(src, g, dst, B)` carries a
Boolean guard `g` (a BDD over `AP`) and the set `B ⊆ {1,…,m}` of acceptance sets
it belongs to. A run is accepting iff for every set `i` it takes infinitely many
`i`-marked edges (transition-based generalized Büchi).

## The rejecting star

daisystar applies at the **initial SCC** `C` (the SCC of `q0 = h`) when two purely
local conditions hold:

- **`C` is rejecting**: no accepting run stays inside `C` forever (Spot decides
  this directly, `is_rejecting_scc`). Then any run confined to `C` is
  non-accepting, so accepting ⟺ *leaving* `C` — the reachability regime.
- **`C` is a length-1 star** at `h`: every state other than `h` is one hop from
  `h`. Split the hub's out-edges into **petals** (self-loops `h → h`), **entries**
  (`h → s`, `s ∈ C`), and **hub stems** (`h → dst`, `dst ∉ C`); each other state
  `s ∈ C` is a **spoke** whose out-edges target only itself (a self-loop **body**),
  the hub (a **return**), or outside `C` (a **spoke stem**). An edge from a spoke
  to a third state of `C` is a longer detour and fails the test.

Those two tests are the whole accept/decline boundary: necessary, sufficient, and
local. The SCC boundary (no edge into `C` from outside) holds for free — `C` is the
initial SCC. Abbreviate, per spoke `s`:

```
σ    = ⋁ { g : petal (g) }                            -- all petal guards
E_s  = ⋁ { g : entry  h →(g) s }                      -- enter spoke s
G_s  = ⋁ { g : body   s →(g) s }                      -- loop in spoke s   (⊥ if none)
R_s  = ⋁ { g : return s →(g) h }                      -- return to the hub
φ_k  = Λ( of(A↓dst_k) )                               -- child label of an exit target
```

where exits are the hub stems `(g_j, dst_j)` and the spoke stems `(h_k, dst_k)`,
and `A↓dst` is the sub-automaton rooted at `dst`, rewrapped as a `Language` by
`of(·)`.

## The label

`C` is rejecting, so staying forever rejects: the language is exactly the
reachability part — finitely many stay-moves at the hub, then an exit to a child.

```
Final(h)  =  LEAVE(h)                                  -- STAY∞ is empty, by rejection
stay      =  σ  ∨  ⋁_s ( E_s ∧ X(G_s U R_s) )  ∨  ⋁_s ( G_s U R_s )
LEAVE(h)  =  stay  U  ⋁ ( exit moves )
```

### The moves

- **Stay** (the left of the `U`). A petal letter `σ`, a full spoke excursion
  `E_s ∧ X(G_s U R_s)` (enter, loop the body, return to the hub), or the in-body
  residual `G_s U R_s` (so `stay` still holds while a run is mid-excursion).
- **Leave from the hub** (an exit disjunct): `g_j ∧ X φ_j` — take a hub stem now,
  `φ_j` after.
- **Leave from a spoke** (an exit disjunct): `E_s ∧ X( G_s U ( h_k ∧ X φ_k ) )` —
  the spoke excursion with the return replaced by a spoke stem: enter, loop the
  body, then exit to the child. The strong `U` forces the exit actually to fire.

### Degenerate cases (no special-casing)

- **a spoke with no body** (`G_s = ⊥`): `⊥ U ψ ≡ ψ`, so its excursion is
  `E_s ∧ X R_s` and its exit is `E_s ∧ X(h_k ∧ X φ_k)` — the rigid two-step detour.
- **no spokes**: `stay = σ` and `LEAVE = σ U ⋁_j(g_j ∧ X φ_j)` — exactly `daisy`'s
  leave, the self-loop reachability case.
- **a true accepting sink** as an exit target: the child returns `⊤`, so an exit
  `… ∧ X ⊤` drops its tail.

## The translator

```
daisystar(Λ) : Translator
daisystar(Λ)(L) =
    let A = tgba(L); h = init(A) in
    if not isRejecting(scc(h))      then ⊥        -- not the reachability regime
    else case starPartition(A, h) of
      ⊥                              -> ⊥          -- not a length-1 star
      (petals, spokes, stems)        ->
        let φ_k = Λ( of(A↓dst_k) )  for each exit target dst_k
        in if any φ_k = ⊥ then ⊥                   -- a declined child poisons C
           else Some( LEAVE(h, [φ_k]) )            -- adopted under the gate (below)
```

A single declined exit child poisons `C`, exactly as a daisy stem does.

## Soundness and exactness

`STAY∞ = false` is **exact by the rejecting-SCC test** — a run confined to `C`
collects no accepting condition, so it cannot accept. That half needs no oracle.

The `LEAVE` form above is **complete** (`L(A) ⊆ LEAVE`) but **not sound in
general** (`LEAVE ⊋ L(A)` can happen), so daisystar — like `partscc` — adopts `φ`
**only** when `are_equivalent(A, translate(φ))` holds, and declines otherwise.

- *Completeness* is clean. Every accepting run leaves `C` after a finite walk on
  the star: complete hub moves (a petal, or a full excursion `E_s·G_s*·R_s`),
  then an exit move. Read off the `U` — the exit position satisfies an exit
  disjunct; every earlier position is a petal start (`σ`), an excursion start
  (`E_s ∧ X(G_s U R_s)`), or inside/at-the-end-of a body (`G_s U R_s`). The loose
  body residual only helps here.
- *Soundness fails* because `stay` is a **pointwise** disjunction: a word can
  satisfy it at every position via *inconsistent* disjuncts that never chain into
  a legal walk. The culprit is the standalone `(G_s U R_s)` disjunct — it holds at
  a **hub** position where the legal run has no move (a *stuck* hub), wrongly
  admitting the word. This is `daisy2`'s hub-looseness, inherited verbatim.

**A witness** (`tests/fixtures/daisystar_loose.hoa`). Letters `a,b,c,d` disjoint;
hub `h` has only `h →[a] s` — no petal, no hub-stem, so `h` is stuck on `b/c/d`.
Spoke `s`: body `b`, return `c`, spoke-exit `d` to a true sink. `C = {h,s}` is
rejecting. Then `L(A) = (a b* c)* a b* d · Σ^ω`, but the emitted

```
LEAVE = ((b U c) ∨ (a ∧ X(b U c)))  U  (a ∧ X(b U d))
```

accepts `c·a·d^ω`: position 0 reads `c`, where `(b U c)` holds immediately, so
`stay` passes a hub letter that has no legal move — yet no run of `A` starts on
`c`. The gate catches it (`too loose: c·a·d^ω`) and daisystar declines. On the
benchmark this never fired (61/61 candidates adopted): natural automata have an
effectively total hub whose stuck letters don't start a body word, so the flat
form is correct there. But the gate is **necessary**, not decorative.

Guards (`σ`, `E_s`, `G_s`, `R_s`) are symbolic: no `2^AP` enumeration, no
determinization. Work and output size scale with states and edges, not the
alphabet.

## The exact LEAVE: a two-phase anchored fixpoint (the fix)

The defect is that the flat `stay` forgets *which phase* the run is in. A
daisystar is really **two states linked by `X` connectors, each with a `U`
self-loop, iterated until an exit**: the hub `h` (self-loop = the petals) and a
spoke `s` (self-loop = the body `G_s`), with entry and return the `X` connectors
between them. Naming the two phases as mutually-recursive obligations threads the
phase structurally through the `X`s — so a body letter is reachable **only after
its entry**, and the standalone-residual looseness is gone by construction:

```
Stay_h  =  ⋁_j ( g_j ∧ X φ_j )          -- exit from the hub
        ∨  ⋁_p ( σ_p ∧ X Stay_h )        -- a petal, still at the hub   (the hub's U)
        ∨  ⋁_s ( E_s ∧ X Stay_s )        -- enter spoke s               (X connector)

Stay_s  =  ⋁_k ( h_k ∧ X φ_k )           -- exit from spoke s
        ∨  ( G_s ∧ X Stay_s )            -- a body letter, still in s   (the spoke's U)
        ∨  ( R_s ∧ X Stay_h )            -- return to the hub           (X connector)

LEAVE_exact  =  Stay_h        -- LEAST fixpoint: a run must reach an exit
```

Each phase's "keep looping ∨ escape" *is* an until: `Stay_s` unfolds to
`G_s U ( (R_s ∧ X Stay_h) ∨ ⋁_k (h_k ∧ X φ_k) )` — loop the body until you return
or exit; and the hub's petal loop is `σ U (…)`. Because the obligation is anchored
at `q0 = h` and propagated only through these `X`s, there is **no standalone
`(G_s U R_s)` disjunct**: the witness above cannot arise, and `LEAVE_exact` is
sound — the construction would be **exact**, retiring the gate.

This is the **least-fixpoint** (reachability) analog of `daisy2`'s open `Φ_stay`
safety problem — and the easier side: with no spokes it already collapses to
`daisy`'s `LEAVE = σ U EXIT`, and `μZ.(ψ ∨ α ∧ XZ) = α U ψ` is finite. The one open
step is the finite-LTL closed form of the *multi-move* μ (petals interleaved with
excursions); it exists (the language is star-free) and is the reachability face of
the daisychain move-level closed form. Until it lands, daisystar emits the flat
`LEAVE` under the gate; the anchored form is the path to dropping the gate.

## Out of scope (the assembly's concern)

daisystar computes one rejecting star's `LEAVE` and trusts its inputs. Pushed to
the assembly that drives the labeling: the child `Λ` being well-founded; closing
the open recursion with a fixpoint `Λ*` and the first-fit dispatch around it;
memoization by state for DAG sharing; and the peel order — daisystar sits after
`daisy` and `daisy2` in the `daisy_trio` peel, taking a rejecting star the
recurrence peels decline. A deeper exit trigger (a longer detour, e.g.
`F(a & X(a & X b))`) is not a length-1 star and belongs to the full daisychain,
not here.
