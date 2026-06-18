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

The SCC is **presented in hub form**: a single hub state `h ∈ C` is given such
that deleting it leaves `C ∖ {h}` **acyclic up to self-loops** — a DAG of
self-loops, i.e. a **very-weak** graph. That is daisy's exact fragment, which is
what lets the recursion close. (Computing such an `h` — a feedback vertex set of
`C`, possibly a *set* of states for a fat SCC — is a separate generalization the
assembly owns; this note takes the hub as a precondition and says no more about
choosing it.)

### Petals, stems, detours

Partition `h`'s out-edges three ways:

```
petals   SL(h)  =  self-loops  h →[g] h                           -- one letter, as in daisy
detours  D(h)   =  entries     h →[γ_d] s_d   (s_d ∈ C ∖ {h})     -- back into the SCC
stems    EX(h)  =  exits        h →[g_j] dst_j (dst_j ∉ C)        -- leave the SCC, descend
```

A **detour** `d` is the family of finite paths that begin with an entry edge
`h →[γ_d] s_d`, run through `C ∖ {h}`, and come back to `h`. Since `C ∖ {h}` is
acyclic up to self-loops the path cannot revisit `h` in the middle; since the
detour is finite it *must* return (next section). It is a *big self-loop*: a
self-loop on `h` whose "letter" is a finite-word language, not a single symbol.

### Folding a detour: delegate to a finite-word labeler

The detour sub-automaton `A↓s_d` — rooted at `s_d`, kept inside `C ∖ {h}`, with
every return edge `· →[r] h` redirected to a fresh placeholder exit `•` ("control
is back at the hub") — describes a **finite-word language** `R_d` (every word ends
by returning to `h`). daisychain hands it to a **finite-word labeler** `Λ_f` and
gets back an opaque label for `R_d` that it **never inspects** — the compositional
seam, the daisychain analog of daisy delegating an LTL label to a child:

```
Λ_f  :  FiniteLanguage → Label_f       -- a translator for finite words (LTL_f / co-safety)
```

**daisychain depends only on the *finiteness* of `R_d`, not on which `Λ_f` is
used.** `Λ_f` is a pluggable parameter, exactly as the child `Λ` is for daisy; we
expect a *family* of `LTL_f` translators (a finite-word daisy, the paper's
`reach`/`solid`/`dashed` reachability machinery — see next — or others), and the
construction below is stated against the abstract `Λ_f`. All daisychain itself
reads back is the move `R_d` and

```
M_d  =  ⋃ { B : B marks some edge along the detour }     -- marks collected per traversal
```

`R_d` being *finite* is the load-bearing assumption: the detour returns. The
genuinely-infinite alternative — *diverge and accept while staying in the detour* —
is a **different** language contribution, owned by `decomp/scc`, not by daisychain
(see Soundness §3). So `R_d`'s only requirement here is finiteness; there is **no**
"detour must avoid certain marks" side condition.

### Finite words are the building block (and the `X̃` boundary)

Why a *finite-word* labeler is the right primitive — and not an accident of this
construction — is visible in the FoSSaCS paper itself (`paper/automata-to-ltl-
construction.md`). Its whole ω-construction is glued out of **finite-prefix
reachability** blocks: the core `reach(S,B,β,T,τ)` means

```
∃ i ≥ 0.  δ(S, w[0..i)) = T  ∧  w[i..] ⊨ τ  ∧  (avoid B on [0..i))
```

— reach a target over a *finite prefix* `w[0..i)`, the continuation carried in the
suffix obligation `τ`; the base case is literally a finite until `(¬β) U τ`. That
is "build infinite words by parts": each part is a finite reachability obligation,
the next part is `τ`. A daisychain detour is exactly such a part —
`R_d` reaching `h`, with `Φ` (the hub continuation) playing the role of `τ` — which
is why `{R_d} ↦ Φ` is the natural seam.

The one subtlety a finite-word labeler must respect: a finite word has a **real
last position**, where `X` is *not* self-dual. `X φ` requires `|w| > 1`, so at the
end `X true ≡ false`, **not** `true` (the identity the infinite-word construction
leans on). The fix is the **weak next** `X̃ ψ := ¬X¬ψ`, true at the last position
and agreeing with `X` elsewhere; the paper's Remark 2 / §10 needs it in exactly one
place — `wsolid` (Formula 4), the *safety* dual that reasons all the way to the
end. For daisychain this is precisely the detour↔hub **handoff**: inside `R_d` the
labeler uses `X̃` at the return edge, and the seam `{R_d} ↦ Φ` reinterprets "end of
the detour word" as "control passes to the infinite continuation `Φ`" (strong `X`
again). Keeping the two regimes — finite body, infinite tail — separated at that
seam is what makes the composition clean.

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

1. **The hub is a daisy in the quotient.** Collapsing each detour to one
   big-self-loop edge `h→h` leaves only self-loops returning to `h`; the SCC
   boundary forbids entry from outside and the hub-form precondition forbids any
   other cycle. So `h` meets the daisy precondition and `STAY∞ ∨ LEAVE` is daisy's
   equation, one level up.

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

## Out of scope (the assembly's concern)

As with daisy: closing the open recursion with a fixpoint `Λ*` and first-fit
dispatch, memoization by state for DAG sharing, the split of labour with
`decomp/scc`, and SCC-iteration order belong to the assembly that wires the child,
not to this local production. **The finite-word labeler `Λ_f` is likewise out of
scope** — daisychain fixes its *contract* (label a finite-word detour language) and
leans only on finiteness; *which* `LTL_f` translator implements it (a finite-word
daisy, the paper's reachability machinery, …) is a separate, pluggable family.
daisychain computes one SCC's label from its hub, its petals, its detours (opaque
finite-word labels), and its stem children.
