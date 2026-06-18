# The daisychain algorithm  (DRAFT — formalization in progress)

> First draft, kept git-inspectable so we can iterate on the formalization
> *before* writing any code. The single-state engine it generalizes is
> `aut2ltl/daisy` (read `daisy/algorithm.md` first — this note reuses its
> notation: petals, stems, `σ`, `σ_i`, `STAY∞`, `LEAVE`). Worked validation of
> the central example lives in `tests/daisychain/probe_bigloop_Gafb.py`.

daisy peels a **single** state whose only cycle is its own self-loop. daisychain
peels a whole **terminal-or-internal SCC** by reducing it to *one* daisy: it picks
a **hub** state `h`, folds every other path that returns to `h` into a **big
self-loop** — a finite, guaranteed-to-return *detour* labelled by recursively
running daisy on the detour itself — and then applies the ordinary
`STAY∞ ∨ LEAVE` production at `h`, treating each big self-loop as a (multi-step)
petal. The name is literal: the hub is a daisy whose petals are themselves
daisies (each detour is very-weak, so daisy labels it), a *chain* of daisies.

## Setting

The Translator/Label contract is unchanged (see `daisy/algorithm.md` §Setting):

```
Label       =  Some φ  |  ⊥
Translator  =  Language → Label
```

daisychain asks the Language for its **TGBA** `A = (Q, Σ, δ, q0, {F_1,…,F_m})`,
`Σ = 2^AP`, transition-based generalized Büchi: an edge `(src, g, dst, B)` carries
a Boolean guard `g` (a BDD over `AP`) and the marks `B ⊆ {1,…,m}`; a run accepts
iff for every set `i` it takes infinitely many `i`-marked edges (`m = 0` ⇒ every
infinite run accepts). It applies at the **initial SCC** `C` (the SCC of `q0`),
which it requires to have no non-self incoming edge from outside `C` — the same
"nothing flows back in" boundary as daisy, lifted from a state to an SCC.

## From SCC to hub: the reduction

### The hub

Pick a **hub** `h ∈ C` that is a **feedback vertex set** of `C`: every cycle of
`C` passes through `h`. (First draft: a *single* hub state; the general FVS is a
set `H`, an open generalization below.) Deleting `h` leaves `C ∖ {h}` **acyclic
up to self-loops** — a DAG of self-loops, i.e. a **very-weak** sub-automaton.
That is exactly daisy's home fragment, which is what lets the recursion close.

### Detours and the big self-loop

Split `h`'s out-edges into three kinds (petals/stems as in daisy, plus detours):

```
petals   SL(h)  =  self-loops   h →[g] h                          -- one-letter, as in daisy
detours  D(h)   =  entries      h →[γ_d] s_d   with s_d ∈ C∖{h}   -- back into the SCC
stems    EX(h)  =  exits        h →[g_j] dst_j with dst_j ∉ C     -- leave the SCC, descend
```

A **detour** `d` is the whole family of finite paths that start with an entry edge
`h →[γ_d] s_d`, wander through `C ∖ {h}` (a DAG of self-loops), and come back to
`h`. Because `h` is an FVS, such a path **cannot revisit `h`** in the middle and
**must** eventually return (it cannot stay forever — see soundness). It is a *big
self-loop*: a self-loop on `h` whose "letter" is a finite word language, not a
single symbol.

### Folding a detour (recursive daisy)

The detour sub-automaton `A↓s_d` — rooted at the entry target `s_d`, restricted to
`C ∖ {h}`, with the return edges `· →[r] h` redirected to a fresh placeholder
"back-at-the-hub" exit `•` — is very-weak. Run daisy on it:

```
β_d  =  daisy( of(A↓s_d  with  ·→h  rerouted to •) )
M_d  =  ⋃ { B : B marks any edge of detour d }        -- entry ∪ internal ∪ return marks
```

`β_d` is a `U`-fragment formula (a finite obligation with the continuation `•`
standing for "control is back at `h`"). `M_d` is the **union of all marks seen
along the detour**, collected onto the folded pseudo-edge — sound because, by the
condition below, no acc set is *trapped* inside the detour. Define the **big-self-
loop move**

```
τ_d  =  γ_d ∧ β_d            -- take entry guard now, discharge the body, return to h
```

so that returning to `h` re-enters the hub's own formula (the fixpoint, closed by
`β_d`'s finiteness).

## The label

Generalize daisy's petal aggregates to include the big self-loops:

```
σ̃    =  σ  ∨  ⋁_{d ∈ D(h)} τ_d                       -- "make some stay-move at h"
σ̃_i  =  σ_i ∨ ⋁_{d : i ∈ M_d} τ_d                    -- stay-moves that carry acc set i
```

and reuse the daisy production at `h`:

```
Final(h)  =  STAY∞(h)  ∨  LEAVE(h)
STAY∞(h)  =  G(σ̃)  ∧  ⋀_{i=1..m} GF(σ̃_i)            -- stay in C forever, accepting
LEAVE(h)  =  σ̃  U  ⋁_{j} ( g_j ∧ X φ_j )             -- stay finitely, then exit C via a stem
```

with `φ_j = Λ(of(A↓dst_j))` the child label of SCC-exit stem `j` (`dst_j` strictly
descends, so `Λ` is well-founded there, exactly as in daisy).

### Worked check (`probe_bigloop_Gafb.py`)

`G(a → Xb)` / `G(a ∨ Fb)` has a 2-state initial SCC `0 ⇄ 1`. Hub `h = 0`; one
petal `σ = a∨b {0}`; one detour `0 →[¬a∧¬b] 1, (¬b)*, 1 →[b] 0` with `β_d = ¬b U
b` and `M_d = {0}`. No SCC-exit (`LEAVE = false`). Then

```
STAY∞(0) = G( (a∨b) ∨ (¬a∧¬b ∧ (¬b U b)) ) ∧ GF(…)   ≡   G(a ∨ Fb)
```

verified equivalent to the input — a clean closed form where the `buchi`
technique emits a 48-node blob.

## Why it is sound (sketch)

1. **The hub is a genuine daisy in the quotient.** `h` is an FVS, so in the
   quotient that collapses each detour to a single big-self-loop edge `h→h`, the
   only edges returning to `h` are self-loops (petals and big self-loops). The
   SCC-boundary condition forbids edges into `C` from outside, and `h` being an
   FVS forbids any other cycle. So `h` satisfies the daisy precondition and
   `STAY∞ ∨ LEAVE` is the daisy equation, verbatim, one level up.

2. **Detours are must-return (`*`, not `ω`).** This is the §2.3 lever read one
   level up. A detour stays inside `C ∖ {h}`, whose only cycles are self-loops.
   **Soundness condition (syntactic):** every such internal self-loop must
   **miss at least one acc set** — a clean sufficient form is *no marks on
   detour-internal self-loops* (marks on the chain's successor edges are fine,
   they fold into `M_d`). Then an infinite stay inside a detour is non-accepting,
   so in any accepting run every detour entry is followed by a return to `h`.
   Hence an accepting run that never exits `C` visits `h` **infinitely often** —
   which is what `STAY∞`'s `G/GF` over `σ̃` asserts.

3. **The fold is well-founded.** "Must return" is precisely the `U`
   well-foundedness that breaks the back-edge: `β_d` is a finite `U`-obligation,
   so the hub→detour→hub recursion unfolds to a DAG, never an unbounded fixpoint.
   daisy is *exact on very-weak*, so `β_d` labels the detour exactly.

4. **Mark bookkeeping is faithful.** Because no acc set is trapped inside a
   detour (2), routing the **union** `M_d` onto the pseudo-edge is sound:
   `GF(σ̃_i)` ⟺ "set `i` is seen infinitely often", since each traversal collects
   `i` exactly when the real detour does.

## Degenerate cases (should fall out, like daisy)

- **No detours** ⇒ `D(h)=∅` ⇒ `σ̃ = σ`, `τ_d` absent ⇒ daisychain *is* daisy.
- **No petals, no exits** ⇒ pure recurrence through detours (`G(a∨Fb)` is this).
- **A detour that can never return** would violate the soundness condition and is
  rejected up front (declined), not mis-folded.

## Open points (the formalization to settle before code)

- **`STAY∞` over multi-step moves.** `G(σ̃) ∧ GF(σ̃_i)` re-asserts the detour body
  `β_d` at *every* position, not only at hub-visits. It is exact on the worked
  example (deterministic, single mark), but the general soundness of `G(σ̃)` for
  variable-length moves is the crux. Options to pin down: (a) prove `G(σ̃)` sound
  unconditionally; (b) restrict it to hub-visit positions via a marker; (c)
  reformulate `STAY∞` as an explicit `(σ̃)^ω` ω-regular fixpoint. **This is the
  open question that decides the design.**
- **Multi-state hub `H` (true FVS).** Single-state `h` may not be an FVS of a
  fat SCC; the general construction eliminates a non-singleton `H` topologically.
  Bookkeeping for marks and detours across `|H|>1` is unspecified here.
- **Hub choice.** Minimum FVS vs. "the accepting states" — affects detour count
  and formula size, not soundness (any FVS is sound).
- **`visiting` / well-foundedness guard.** The fold must break the back-edge so
  the recursion the assembly drives stays a DAG; interaction with the existing
  daisy-assembly memoization is unspecified.

## Out of scope (the assembly's concern)

As with daisy: closing the open recursion with a fixpoint `Λ*` and first-fit
dispatch, memoization by state for DAG sharing, and the SCC-iteration order belong
to the assembly that wires the child, not to this local production. daisychain
computes one SCC's label from its hub, its petals, its detours, and its children.
