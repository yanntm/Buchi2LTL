# The daisychain algorithm  (DRAFT — formalization in progress)

> First draft, kept git-inspectable so the formalization can be reviewed *before*
> any code. It generalizes the single-state engine in `aut2ltl/daisy` — read
> `daisy/algorithm.md` first; this note reuses its vocabulary (petals, stems,
> guard `σ`, the `STAY∞ ∨ LEAVE` production). The central example is checked in
> `tests/daisychain/probe_bigloop_Gafb.py`.

daisy peels a **single** state whose only cycle is its own self-loop. daisychain
peels a whole **SCC** by reducing it to *one* daisy: choose a **hub** state `h`,
fold every path that leaves `h` and returns into a **big self-loop** — a finite,
guaranteed-to-return *detour* whose label is obtained by running daisy on the
detour itself — and then apply the ordinary daisy production at `h`, with each big
self-loop treated as a multi-step petal. The name is literal: the hub is a daisy
whose petals are themselves daisies. The one idea that makes this work cleanly is
to read the stay condition as **"always inside a stay-move"**, not "a stay-move
starts at every step" (see *Stay-moves: start vs. in-progress*).

## Setting

The Translator/Label contract is unchanged:

```
Label       =  Some φ  |  ⊥                       -- φ an LTL formula; ⊥ = decline
Translator  =  Language → Label
```

daisychain asks the Language for its **TGBA** `A = (Q, Σ, δ, q0, {F_1,…,F_m})`,
`Σ = 2^AP`, transition-based generalized Büchi: an edge `(src, g, dst, B)` carries
a Boolean guard `g` (a BDD over `AP`) and the marks `B ⊆ {1,…,m}`; a run accepts
iff for every set `i` it takes infinitely many `i`-marked edges (`m = 0` ⇒ every
infinite run accepts). It applies at the **initial SCC** `C` (the SCC of `q0`),
required to have no incoming edge from outside `C` — the same "nothing flows back
in" boundary as daisy, lifted from one state to one SCC.

## Reducing an SCC to its hub

### The hub

Choose a **hub** `h ∈ C` that is a **feedback vertex set** of `C`: every cycle of
`C` passes through `h`. (This first draft fixes a *single* hub state; a true FVS
may need a set `H` — see Open points.) Deleting `h` leaves `C ∖ {h}` **acyclic up
to self-loops** — a DAG of self-loops, i.e. a **very-weak** graph. That is daisy's
exact fragment, which is what lets the recursion close.

### Petals, stems, detours

Partition `h`'s out-edges three ways:

```
petals   SL(h)  =  self-loops  h →[g] h                           -- one letter, as in daisy
detours  D(h)   =  entries     h →[γ_d] s_d   (s_d ∈ C ∖ {h})     -- back into the SCC
stems    EX(h)  =  exits        h →[g_j] dst_j (dst_j ∉ C)        -- leave the SCC, descend
```

A **detour** `d` is the family of finite paths that begin with an entry edge
`h →[γ_d] s_d`, run through `C ∖ {h}`, and come back to `h`. Since `h` is an FVS,
such a path cannot revisit `h` in the middle, and — by the must-return property
below — must eventually return. It is a *big self-loop*: a self-loop on `h` whose
"letter" is a finite-word language rather than a single symbol.

### Folding a detour: recursive daisy

The detour sub-automaton `A↓s_d` — rooted at `s_d`, kept inside `C ∖ {h}`, with
every return edge `· →[r] h` redirected to a fresh placeholder exit `•` ("control
is back at the hub") — is very-weak, so daisy labels it **exactly**. Running daisy
gives, for each detour state `s`, a residual formula `ψ_s` (a `U`-fragment
obligation reaching `•`), and in particular the body `β_d = ψ_{s_d}`. Collect

```
M_d  =  ⋃ { B : B marks some edge of detour d }     -- entry ∪ internal ∪ return marks
```

the **union of marks seen along the detour**, routed onto the folded pseudo-edge —
sound because, by the must-return condition, no acc set is trapped inside the
detour.

## The label

### Stay-moves: start vs. in-progress

This is the crux, and where a naive lift of daisy goes wrong. daisy's stay
condition is `G(σ)` with `σ` a **Boolean over `AP`**: every position *is* a
one-letter petal, so "stay" and "a petal at this step" coincide. A big self-loop
spans several positions, so `σ` becomes **temporal** and the two notions split:

- a *move-start* predicate is true only where a move *begins* (a hub-visit);
- an *in-move* predicate is true at *every* position the run occupies while making
  a valid move — at the petal letter, and at each corridor position of a detour.

The fix is to make `G` iterate the **in-move** predicate. For a detour `d`, the
in-move obligation at a corridor position where control sits at state `s` is
exactly daisy's residual `ψ_s`: it asserts the remaining detour will complete and
return. Define

```
ρ_d  =  ⋁_{s ∈ detour d} ψ_s            -- "currently somewhere inside detour d"
σ̃    =  σ  ∨  ⋁_{d ∈ D(h)} ρ_d           -- "currently inside some stay-move"
```

The entry position (at `h`, reading `γ_d`) is the first position of `ρ_d`; when
`γ_d` overlaps the detour's first residual it is subsumed by `ρ_d` (as it is in the
worked example, so the entry guard drops out), otherwise it is carried as that
residual's leading conjunct. `σ̃` is the in-move predicate; `G(σ̃)` reads "the run
never steps outside a valid stay-move", i.e. it stays in `C` forever.

### STAY∞ and LEAVE

```
Final(h)  =  STAY∞(h)  ∨  LEAVE(h)
STAY∞(h)  =  G(σ̃)  ∧  ⋀_{i=1..m} GF(μ_i)            -- stay in C forever, accepting
LEAVE(h)  =  σ̃  U  ⋁_{j} ( g_j ∧ X φ_j )            -- stay finitely, then exit C via a stem
```

`φ_j = Λ(of(A↓dst_j))` is the child label of SCC-exit stem `j`; `dst_j` strictly
descends, so `Λ` is well-founded there, exactly as in daisy. `LEAVE` reuses the
same `σ̃`: holding inside the SCC until a genuine exit.

### Acceptance

`μ_i` is the position-predicate "an `i`-marked edge of `C` fires here":

```
μ_i  =  σ_i  ∨  ⋁_{d : i ∈ M_d} ( the i-marked edge of detour d fires )
```

with `σ_i` the petals carrying set `i` (as in daisy). Because the detour is
must-return, set `i` is collected once per traversal at a fixed marked edge, so
`GF(μ_i)` ⟺ "set `i` infinitely often". The precise position-predicate for the
detour-internal marked edge — derived from daisy's labeling of the detour — is the
one piece still to be pinned (Open points). When `m = 1` and a petal already
carries the set (the worked example), `GF(μ_1)` is implied by `G(σ̃)` and vanishes.

### Worked check (`probe_bigloop_Gafb.py`)

`G(a → Xb)` / `G(a ∨ Fb)` has a 2-state initial SCC `0 ⇄ 1`. Hub `h = 0`; one
petal `σ = a∨b {0}`; one detour `0 →[¬a∧¬b] 1, (¬b)*, 1 →[b] 0` with body
`β_d = ¬b U b`, residual `ρ_d = ¬b U b`, and `M_d = {0}`. No SCC-exit, so
`LEAVE = false`. Then

```
σ̃ = (a∨b) ∨ (¬b U b)          STAY∞(0) = G(σ̃) ∧ GF(…)  ≡  G(a ∨ Fb)
```

verified equivalent to the input (the entry guard `¬a∧¬b` drops out — `σ̃` is the
in-move predicate, confirmed against the move-start variant in the probe), and the
`GF` conjunct is implied. The `buchi` technique emits a 48-node blob for the same
language.

## Soundness (sketch)

1. **The hub is a genuine daisy in the quotient.** `h` is an FVS, so in the
   quotient that collapses each detour to one big-self-loop edge `h→h`, the only
   edges returning to `h` are self-loops (petals and big self-loops); the SCC
   boundary forbids entry from outside, and the FVS property forbids any other
   cycle. So `h` meets the daisy precondition and `STAY∞ ∨ LEAVE` is daisy's
   equation, one level up.

2. **Detours must return (`*`, not `ω`).** A detour stays in `C ∖ {h}`, whose only
   cycles are self-loops. **Soundness condition (syntactic on the TGBA):** every
   such internal self-loop must miss at least one acc set — a clean sufficient form
   is *no marks on detour-internal self-loops* (marks on the chain's successor
   edges are fine; they fold into `M_d`). Then an infinite stay inside a detour is
   non-accepting, so in any accepting run every detour entry is followed by a
   return to `h`; a run that never exits `C` therefore visits `h` infinitely often.
   This is the lever: the *accepting bit chooses the operator* — a non-accepting
   internal cycle is a finite `*` (a `U`), an accepting recurrence at the hub is an
   `ω` (a `G`/`GF`). daisychain reads that dichotomy one level above daisy.

3. **The fold is well-founded.** "Must return" is precisely the `U`
   well-foundedness that breaks the back-edge: each `ψ_s` is a finite `U`
   obligation, so the hub→detour→hub recursion unfolds to a DAG, never an unbounded
   fixpoint. daisy is exact on very-weak, so the `ψ_s` label the detour exactly.

4. **Marks are faithful.** No acc set is trapped inside a detour (2), so routing
   the union `M_d` onto the pseudo-edge and testing `GF(μ_i)` is sound: each
   traversal collects `i` exactly when the real detour does.

## Degenerate cases (should fall out, as in daisy)

- **No detours** ⇒ `σ̃ = σ` and `μ_i = σ_i` ⇒ daisychain *is* daisy.
- **No petals, no exits** ⇒ pure recurrence through detours (`G(a∨Fb)` is this).
- **A detour that cannot return** violates the soundness condition and is declined
  up front, never mis-folded.

## Open points (to settle before code)

- **The acceptance predicate `μ_i`.** STAY∞'s `GF(μ_i)` needs the exact
  position-predicate for "the `i`-marked edge of detour `d` fires", read off daisy's
  labeling of the detour. Tractable, not yet written.
- **Entry/corridor coverage.** `σ̃` drops the entry guard when `γ_d` overlaps the
  first residual (the worked case). When they are disjoint the entry must be kept
  as the residual's leading conjunct; the general `σ̃` must state this precisely so
  `G(σ̃)` is neither too strong nor too weak.
- **Multi-state hub (true FVS).** A single hub state may not be an FVS of a fat
  SCC; the general construction eliminates a non-singleton `H` topologically. Mark
  and detour bookkeeping across `|H| > 1` is unspecified here.
- **Hub choice.** Minimum FVS vs. "the accepting states" — affects detour count and
  formula size, not soundness (any FVS is sound).

## Out of scope (the assembly's concern)

As with daisy: closing the open recursion with a fixpoint `Λ*` and first-fit
dispatch, memoization by state for DAG sharing, and SCC-iteration order belong to
the assembly that wires the child, not to this local production. daisychain
computes one SCC's label from its hub, its petals, its detours, and its children.
