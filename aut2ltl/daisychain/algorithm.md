# The daisychain algorithm  (DRAFT — formalization in progress)

> First draft, kept git-inspectable so the formalization can be reviewed *before*
> any code. It generalizes the single-state engine in `aut2ltl/daisy` — read
> `daisy/algorithm.md` first; this note reuses its vocabulary (petals, stems,
> guard `σ`, the `STAY∞ ∨ LEAVE` production). The central example is checked in
> `tests/daisychain/probe_bigloop_Gafb.py`.
>
> **Output is pure LTL** — no past operators, no PSL/SERE, no tricks. Finite-word
> (`*`-language) notation appears below only as *internal construction
> scaffolding* for a detour; it is always unfolded to LTL before output (it can
> be — see *Why the output stays LTL*).

daisy peels a **single** state whose only cycle is its own self-loop. daisychain
peels a whole **SCC** by reducing it to *one* daisy: choose a **hub** state `h`,
treat every path that leaves `h` and returns as a **big self-loop** — a finite,
guaranteed-to-return *detour* whose label is an opaque finite-word language handed
in by a child — and then run the ordinary daisy production at `h`, with each big
self-loop treated as a multi-step petal. The name is literal: the hub is a daisy
whose petals are themselves daisies.

## Setting

The Translator/Label contract is unchanged:

```
Label       =  Some φ  |  ⊥                       -- φ an LTL formula; ⊥ = decline
Translator  =  Language → Label
```

daisychain asks the Language for its **TGBA** `A = (Q, Σ, δ, q0, {F_1,…,F_m})`,
`Σ = 2^AP`, transition-based generalized Büchi: an edge `(src, g, dst, B)` carries
a Boolean guard `g` (a BDD over `AP`) and marks `B ⊆ {1,…,m}`; a run accepts iff
for every set `i` it takes infinitely many `i`-marked edges (`m = 0` ⇒ every
infinite run accepts). It applies at the **initial SCC** `C` (the SCC of `q0`),
required to have no incoming edge from outside `C` — the same "nothing flows back
in" boundary as daisy, lifted from one state to one SCC.

## Reducing an SCC to its hub

### The hub

Choose a **hub** `h ∈ C` that is a **feedback vertex set** of `C`: every cycle of
`C` passes through `h`. (This draft fixes a *single* hub state; a true FVS may need
a set `H` — see Open points.) Deleting `h` leaves `C ∖ {h}` **acyclic up to
self-loops** — a DAG of self-loops, i.e. a **very-weak** graph. That is daisy's
exact fragment, which is what lets the recursion close.

### Petals, stems, detours

Partition `h`'s out-edges three ways:

```
petals   SL(h)  =  self-loops  h →[g] h                           -- one letter, as in daisy
detours  D(h)   =  entries     h →[γ_d] s_d   (s_d ∈ C ∖ {h})     -- back into the SCC
stems    EX(h)  =  exits        h →[g_j] dst_j (dst_j ∉ C)        -- leave the SCC, descend
```

A **detour** `d` is the family of finite paths that begin with an entry edge
`h →[γ_d] s_d`, run through `C ∖ {h}`, and come back to `h`. Since `h` is an FVS it
cannot revisit `h` in the middle; since the detour is finite it *must* return (next
section). It is a *big self-loop*: a self-loop on `h` whose "letter" is a
finite-word language, not a single symbol.

### Folding a detour: delegate, don't crack it open

The detour sub-automaton `A↓s_d` — rooted at `s_d`, kept inside `C ∖ {h}`, with
every return edge `· →[r] h` redirected to a fresh placeholder exit `•` ("control
is back at the hub") — is very-weak, so a child labels it. The child returns the
detour's **finite-word language** `R_d`: an opaque `*`-language (a star-free SERE /
`U`-fragment obligation) that daisychain **never inspects**. This is the
compositional seam — the daisychain analog of daisy delegating an LTL label to a
child. All daisychain reads back is `R_d` (the move) and

```
M_d  =  ⋃ { B : B marks some edge along the detour }     -- marks collected per traversal
```

`R_d` being a *finite-word* language is the load-bearing assumption: the detour
returns. The genuinely-infinite alternative — *diverge and accept while staying in
the detour* — is a **different** language contribution, owned by `decomp/scc`, not
by daisychain (see Soundness §3). So `R_d`'s only requirement here is finiteness;
there is **no** "detour must avoid certain marks" side condition.

## The label

### Moves, and the hub anchor

A **stay-move** at `h` is either a petal (one letter satisfying some `g`) or a
detour (one finite word of some `R_d`):

```
M  =  { petals σ }  ∪  { detours R_d }
```

There is **no `atQ0` proposition** — `Σ = 2^AP` has no name for "control is at
`h`". The hub is anchored *functionally*: a stay-move is available exactly where
the run is at `h`, and "the run is at `h` with this future" is the fixpoint `Φ`
itself:

```
Φ  =  ⋁_petals ( σ ∧ X Φ )          -- one letter, then back at h
   ∨  ⋁_detours ( {R_d} ↦ Φ )        -- one R_d-word, then back at h   ({·} = scaffolding)
   ∨  ⋁_stems ( g_j ∧ X φ_j )        -- leave the SCC (a descending child label φ_j)
```

`{R_d} ↦ Φ` ("a word of `R_d` matches from here, and `Φ` holds at its end") is the
finite-word-then-continue connective — written with `*`-language scaffolding,
unfolded to LTL on the way out. `Φ` is the semantic target; the construction's job
is its **closed LTL form**, which is the daisy production lifted from letters to
moves:

```
Final(h)  =  STAY∞(h)  ∨  LEAVE(h)
STAY∞(h)  =  accepting  (M)^ω                       -- stay in C forever, accepting
LEAVE(h)  =  (M)*  then a stem exit  g_j ∧ X φ_j     -- stay finitely, then exit C
```

When every move is a single letter (`D(h) = ∅`) this is *exactly* daisy:
`STAY∞ = G(σ) ∧ ⋀_i GF(σ_i)`, `LEAVE = σ U ⋁_j(g_j ∧ X φ_j)`. The open work is the
move-level lift of these for `|word| > 1` — well-posed because `(M)^ω` over
star-free moves is itself star-free, hence LTL (Open points).

### Acceptance

`STAY∞`'s acceptance counts marks collected at **move completions** (a petal taken,
or a detour traversed back to `h`): for each set `i`,

```
GF( σ_i  ∨  ⋁_{d : i ∈ M_d} "a detour carrying i completes" )
```

This is sound *because* accepting runs revisit `h` (Soundness §3): every mark that
matters is collected on a finite traversal, so there is no need to track marks
inside a detour — the relaxation you get from handing divergence to `decomp/scc`.

### Worked check (`probe_bigloop_Gafb.py`)

`G(a → Xb)` / `G(a ∨ Fb)` has a 2-state initial SCC `0 ⇄ 1`. Hub `h = 0`; one
petal `σ = a∨b {0}`; one detour with `R_d = {¬a∧¬b ; (¬b)[*] ; b}` (spot folds it
to `{{!a&&!b};b[->]}`) and `M_d = {0}`; no SCC-exit, so `LEAVE = false`. The single
detour move discharges `{R_d} ↦ ⊤  ≡  ¬a∧¬b∧Fb` (checked in spot), and the closed
`STAY∞` unfolds to

```
G( (a∨b)  ∨  (¬a∧¬b ∧ Fb) )   ≡   G(a ∨ Fb)
```

— pure LTL, equivalent to the input, where the `buchi` technique emits a 48-node
blob. (The `GF` conjunct is implied here and vanishes.)

## Soundness (sketch)

1. **The hub is a daisy in the quotient.** `h` is an FVS, so collapsing each detour
   to one big-self-loop edge `h→h` leaves only self-loops returning to `h`; the SCC
   boundary forbids entry from outside and the FVS property forbids any other cycle.
   So `h` meets the daisy precondition and `STAY∞ ∨ LEAVE` is daisy's equation, one
   level up.

2. **Detours are finite (must return).** This is the structural core: a detour is a
   finite path from `h` back to `h`, so its label `R_d` is a finite-word language
   and the back-edge to `h` is *broken* in the fold — the hub→detour→hub recursion
   unfolds to a DAG, never an unbounded fixpoint. Finiteness, not mark placement, is
   why the construction terminates and is exact.

3. **Division of labour with `decomp/scc`.** If a run can *diverge and accept while
   staying inside a detour* (an accepting cycle within `C ∖ {h}`), that ω-behaviour
   is a separate contribution that the SCC decomposition handles; daisychain assumes
   (assembly-provided, as daisy assumes well-foundedness) that **every accepting run
   revisits `h` infinitely**. Under that assumption marks need only be collected on
   finite traversals — so the mark conditions are *light*, far weaker than a "detour
   must avoid an acc set" rule.

4. **Why the output stays LTL.** daisychain only *claims* an answer when the
   language is LTL-definable, i.e. **star-free** (Kamp / McNaughton–Papert). Then
   every detour `R_d` is a star-free `*`-language and `{R_d} ↦ Φ` is re-expressible
   in pure LTL; `(M)^ω` over star-free moves is star-free, hence LTL. SERE is only
   the intermediate; the emitted formula is plain LTL. A genuinely non-star-free
   detour (a counter, "even number of `c`") means the SCC is not LTL-definable, and
   daisychain **declines** — matching the tool's soundness/completeness contract.

## Degenerate cases (should fall out, as in daisy)

- **No detours** ⇒ `M = {σ}` ⇒ daisychain *is* daisy.
- **No petals, no exits** ⇒ pure recurrence through detours (`G(a∨Fb)` is this).
- **A detour that cannot return** is not a detour (no finite `R_d`); the offending
  SCC is left to `decomp/scc` or declined, never mis-folded.

## Open points (to settle before code)

- **The move-level closed form.** The real remaining math: the LTL closed form of
  *accepting* `(M)^ω` and of `(M)* ; exit` when moves are multi-letter — the lift of
  daisy's `G(σ)∧⋀GF(σ_i)` and `σ U …`. Well-posed (star-free `(M)^ω ∩ accept` → LTL)
  but not yet written; this is what decides the construction.
- **The functional hub anchor.** With no `atQ0` proposition, is "a stay-move
  starts/continues here" (`σ ∨ ⋁_d γ_d` and the detour residuals) a sufficient proxy
  to pin the closed form, or does the fixpoint need more? To validate.
- **Multi-state hub (true FVS).** A single hub state may not be an FVS of a fat SCC;
  the general construction eliminates a non-singleton `H` topologically. Mark and
  detour bookkeeping across `|H| > 1` is unspecified here.
- **Hub choice.** Minimum FVS vs. "the accepting states" — affects detour count and
  formula size, not soundness (any FVS is sound).

## Out of scope (the assembly's concern)

As with daisy: closing the open recursion with a fixpoint `Λ*` and first-fit
dispatch, memoization by state for DAG sharing, the split of labour with
`decomp/scc`, and SCC-iteration order belong to the assembly that wires the child,
not to this local production. daisychain computes one SCC's label from its hub, its
petals, its detours (opaque `*`-language children), and its stem children.
