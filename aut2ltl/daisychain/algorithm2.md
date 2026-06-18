# daisychain, degenerate case: one-step detours  (DRAFT)

> A deliberately small step between `daisy` (peel one self-loop state) and the
> full `daisychain` (peel a whole SCC; see `algorithm.md`). Read
> `daisy/algorithm.md` for the vocabulary (petals, stems, guard `σ`, the
> `STAY∞ ∨ LEAVE` production); read `algorithm.md` for the general target. This
> note solves the **smallest** non-trivial generalization and is meant to be
> *folded back* into `algorithm.md` once it checks out.
>
> Method: build from the small case, get it exact, then generalize. Two
> simplifications below; the first is **shared** with the eventual general
> construction, the second is **specific** to this degenerate version.
>
> **Output is pure LTL.** No past operators, no PSL/SERE, no finite-word labeler
> `Λ_f` — in this case the SERE scaffolding of `algorithm.md` collapses to a
> single `U`, so we never need an opaque finite-word seam at all.

## The two simplifications

### S1 (shared): the hub is given — drop FVS

`algorithm.md` *chooses* a hub by computing a feedback vertex set of the SCC.
Drop that entirely. We **assume the SCC is presented in hub form**: a
distinguished hub state `h` is given, and `C ∖ {h}` contains only self-loops —
no cycle of `C` avoids `h`. Equivalently: *assume the initial SCC already is a
daisy core at `h`*. The FVS theory is the *mechanism* that would establish this
precondition; here we simply take it as a precondition and leave the search to
the assembly. (For the initial SCC we use `h = q0`.)

### S2 (this version): detours are length 1 in states

The general detour is a finite path `h → s_1 → … → s_k → h` through a DAG of
self-loop states (`k ≥ 1`). Here we add: **`C ∖ {h}` is an antichain** — there
are no edges between distinct non-hub states. So `k = 1` always: the SCC is a
**star**.

```
        E_s ↘        ┌── G_s (self-loop, optional)
   h  ─────────►  s ─┘
   ▲  ◄─────────
        R_s ↗
```

Every detour is one hop out, an optional stay, one hop back:

```
h ─[E_s]→ s ─[G_s]*→ s ─[R_s]→ h            (the spoke s)
```

Each spoke `s ∈ C ∖ {h}` is itself a one-state daisy. The whole SCC is a hub
daisy whose petals are joined by single-daisy spokes — the literal smallest
"daisy of daisies". This is exactly the regime where the opaque finite-word
language `R_d` of `algorithm.md` is a *single* daisy excursion, so its label is
closed-form (a strong `U`) and the `Λ_f` seam is unnecessary.

## Setting

Same contract and same boundary as `algorithm.md`. Ask the Language for its
**TGBA** `A = (Q, Σ, δ, q0, {F_1,…,F_m})`, `Σ = 2^AP`, transition-based
generalized Büchi; an edge `(src, g, dst, B)` carries a Boolean guard `g` (a BDD
over `AP`) and marks `B ⊆ {1,…,m}`; a run accepts iff for every set `i` it takes
infinitely many `i`-marked edges (`m = 0` ⇒ every infinite run accepts). Apply at
the initial SCC `C` (the SCC of `q0`), required to have no incoming edge from
outside `C`. Under S1+S2, `C` is a star with center `h`.

## The pieces

Partition `h`'s out-edges, as in daisy/daisychain:

```
petals  SL(h) = { self-loops  h →[σ] h }                         -- one letter
spokes  D(h)  = { s ∈ C ∖ {h} }                                  -- the detours
stems   EX(h) = { exits  h →[g_j] dst_j,  dst_j ∉ C }            -- leave C, descend
```

For each spoke `s` read off three guards and their marks:

```
E_s   guard of the entry edge   h → s            marks  B_s^E
G_s   guard of s's self-loop    s → s   (⊥ if s has none)   marks  B_s^G
R_s   guard of the return edge  s → h            marks  B_s^R
```

(The single-edge case. Several entries/returns/self-loops on one spoke ⇒ take
the disjunction per role; non-uniform marks across parallel edges are an Open
point.)

## The detour connective

In `algorithm.md` a detour contributes `{R_d} ↦ Φ` — a finite-word language `R_d`
matched, then `Φ` at its end. Under S2 the finite word is `E_s · (G_s)^* · R_s`,
a single daisy excursion, and `{R_d} ↦ Φ` is **directly** an LTL formula:

```
move_s(Φ)  =  E_s ∧ X( G_s U (R_s ∧ X Φ) )
```

Read it as the run reads it: take the entry `E_s` now (edge `h → s`); from the
next position loop at `s` while `G_s` holds, **strong**-until you take a return
`R_s` (edge `s → h`) with `Φ` true at the following position (control back at
`h`). With no self-loop (`G_s = ⊥`) it degenerates, using `⊥ U ψ ≡ ψ`, to the
rigid two-step detour `E_s ∧ X(R_s ∧ X Φ) = E_s ∧ X R_s ∧ X X Φ`.

The until is **strong** on purpose: a run that satisfies `G_s` forever (loops at
`s` and never returns) is *staying in the SCC but never revisiting `h`*. That
ω-behaviour — an accepting cycle inside `C ∖ {h}` — is **not** daisychain's; it
is the `decomp/scc` contribution (`algorithm.md` §3). daisychain assumes every
accepting run revisits `h` infinitely, so every started detour must return.

## The label

The hub fixpoint, exactly daisy's three-way choice with detours as compound
moves:

```
Φ  =  ⋁_petals ( σ ∧ X Φ )                              -- one letter, back at h
   ∨  ⋁_spokes ( E_s ∧ X( G_s U (R_s ∧ X Φ) ) )         -- one excursion, back at h
   ∨  ⋁_stems  ( g_j ∧ X φ_j )                          -- leave C (descending child φ_j)
```

`Φ` is the semantic target; the deliverable is its closed LTL form, daisy's
`Final = STAY∞ ∨ LEAVE` lifted from letters to moves.

### `LEAVE` (finitely many moves, then a stem)

Least fixpoint of `Φ` whose escape is a stem — finitely many stay-moves then
exit `C`. Daisy's `σ U (⋁_j g_j ∧ X φ_j)` becomes the move-level until: keep
taking petals/excursions, finitely often, until a stem fires. The closed form is
`Φ` read as a μ-fixpoint with the stem disjunct as base; concretely it unfolds
along the same `move_s` blocks (no detour may be left mid-excursion — the strong
`U` inside `move_s` already forces each started excursion to complete before the
next choice).

### `STAY∞` (stay in C forever, revisiting h, accepting)

```
STAY∞  =  StaySafe  ∧  ⋀_i GF( comp_i )
```

**Safety part `StaySafe`** lifts daisy's `G(σ)` but must track **phase** — at the
hub vs. inside a spoke body — because the two positions admit different letters.
With no `atQ0` proposition the phase is carried structurally, in two mutually
recursive obligations (`Stay_h` = "staying, at the hub now"; `Stay_s` = "staying,
inside spoke s's body now"):

```
Stay_h  =  ⋁_petals ( σ ∧ X Stay_h )                   -- petal, still at hub
        ∨  ⋁_spokes ( E_s ∧ X Stay_s )                 -- enter spoke s

Stay_s  =  G_s U ( R_s ∧ X Stay_h )                    -- loop, must return to hub
```

`StaySafe = Stay_h`, and `move_s(Φ)` is exactly `E_s ∧ X Stay_s` with
`Stay_h := Φ`. The return `U` is **strong** (each entered spoke must come back);
the petal choice may repeat forever, so the hub obligation is a greatest fixpoint
while each spoke body is a least fixpoint — the `ν`-over-`μ` alternation that *is*
"revisit `h` infinitely". No SERE: each excursion is a single `U` block.

**No flat-`G` shortcut.** The tempting collapse `StaySafe ≟ G( ⋁σ ∨ ⋁_s (G_s U R_s) )`
is **unsound in both directions**, verified in `probe_flatG_side_condition.py`:

- *too strict at entries*, when `E_s ⊭ G_s`: the entry position then satisfies
  neither a petal nor any `G_s U R_s`, so the flat `G` rejects a real staying
  word (witness `e & !g & !p & !r ; cycle{p&r}`);
- *too loose at the hub*, always: a hub position reading `R_s` (or a body letter)
  satisfies `G_s U R_s` with no preceding entry, so the flat `G` accepts a word
  that has no run at all (witness `(g* r)^ω` for a star whose hub is left only by
  `E_s`).

The phase recursion is therefore the definition. It collapses to finite LTL —
daisychain only claims LTL-definable (star-free) languages, where
`(petal + E_s G_s* R_s)^ω` is star-free — and producing that finite closed form
is the move-level lift of daisy's `G(σ)` (Open points). Why the worked example
*looked* flat: a double coincidence, explained below.

**Acceptance `comp_i`.** A TGBA run accepts iff, for **every** acceptance set
`i`, it traverses **infinitely many `i`-marked edges**. We re-express each "set
`i` infinitely often" as an LTL `GF(comp_i)`, with `comp_i` marking the positions
at which an `i`-marked edge of the star is taken. The reduction is legitimate
**because the staying run revisits `h` infinitely** (the daisy2 / `decomp/scc`
split, §3): every edge that can matter lies on a *finite* move — a petal, or one
full spoke excursion — so "an `i`-marked edge is taken infinitely often" is the
same as "infinitely many *moves that carry `i`* complete". A mark inside a body
that the run never leaves does not arise here; that is `decomp/scc`'s case.

The marks sit on the **individual edges** of a move, so `comp_i` must be keyed to
the edge that actually carries `i` — *not* to the spoke as a whole. The three
edge roles give three cases (`move_s(⊤) = E_s ∧ X(G_s U R_s)`, the bare
excursion):

```
comp_i  =  ⋁_{petal σ : i ∈ B_σ}  σ                          -- (P)  a petal edge
        ∨  ⋁_{s : i ∈ B_s^E ∪ B_s^R}  move_s(⊤)              -- (ER) entry / return edge
        ∨  ⋁_{s : i ∈ B_s^G}  E_s ∧ X( G_s ∧ (G_s U R_s) )   -- (G)  a body self-loop edge
```

- **(P)** A petal carrying `i` is one hub self-loop, taken exactly when the letter
  satisfies `σ` at a hub position; `σ` is its own witness, as in daisy.
- **(ER)** The entry edge `h→s` and the return edge `s→h` are taken on **every**
  traversal of `s` — one each, no choice — so the bare excursion `move_s(⊤)`
  already witnesses them: traverse `s`, and the `i`-marked entry/return edge is
  taken.
- **(G)** A body self-loop edge `s→s` carrying `i` is taken **only if the body
  loops at least once**. A traversal that enters and returns with *zero* body
  steps (`E_s` then immediately `R_s`) never touches the self-loop, so it must
  **not** be credited. The witness therefore demands one real body step before
  the return: `E_s ∧ X(G_s ∧ (G_s U R_s))` — at the first post-entry position
  `G_s` holds (the loop is taken once) and `G_s U R_s` carries the excursion on to
  its return.

`GF(comp_i)` then asserts that an `i`-collecting move recurs forever, which —
under the revisits-`h` assumption — is exactly "set `i` infinitely often". With
`m = 0` (no sets) the conjunction is empty and `STAY∞ = StaySafe`.

**Why per-edge, not per-spoke (a real failure to check).** The prototype first
collapsed a spoke's marks to one set `B_s = B_s^E ∪ B_s^G ∪ B_s^R` and used the
bare `move_s(⊤)` for all of them. That is unsound when the mark is on the body.
`GF(a ∧ Xb)` is a one-spoke star whose self-loop carries the only mark; the run
that **enters and returns with no loop** — word `(¬a∧¬b · a)^ω` — completes a
spoke excursion every two steps yet never takes the marked self-loop, so the
language rejects it. The union form wrongly accepted it (probe
`tests/daisy2/probe_daisy2.py 'GF(a & X b)'`, witness `cycle{!a&!b ; a}`). Case
**(G)**'s "≥ 1 body step" guard is exactly the fix; this is the soundness point
to scrutinize.

**Two caveats this draft leaves open** (the acceptance face of the "parallel
edges on a role" Open point):

- *Parallel edges with non-uniform marks.* `E_s`, `G_s`, `R_s` above are the
  *disjunction* of all edges in that role. If only **some** of several parallel
  entry (resp. body, return) edges carry `i`, the role disjunction is too coarse —
  it also fires for the unmarked siblings. Exactness needs per-edge guards, not
  the role disjunction. (Single-edge roles, the common case, are exact.)
- *Existential runs.* `comp_i` is a property of the **word**, while acceptance is
  existential over runs of a possibly nondeterministic automaton; "`comp_i` holds
  here" must coincide with "*some* accepting run takes an `i`-edge here". For the
  star this is benign — a move is a local hub choice and the spoke path is forced
  once entered — but the exactness of the whole `StaySafe ∧ ⋀_i GF(comp_i)`
  conjunction *is* the unsolved closed form, which is why daisy2 keeps the Spot
  validity gate (`partscc` pattern) and only adopts a candidate it confirms
  equivalent.

## Worked check (`tests/daisychain/probe_bigloop_Gafb.py`)

`G(a → Xb)` ≡ `G(a ∨ Fb)`. Initial SCC `0 ⇄ 1`; hub `h = 0`.

```
petal   σ   = a∨b        marks {0}
spoke s=1:  E_s = ¬a∧¬b   G_s = ¬b   R_s = b      marks {0}
stems       none  ⇒  LEAVE = false
```

The detour move discharges (continuation `⊤`):

```
move_s(⊤) = (¬a∧¬b) ∧ X( ¬b U (b ∧ X⊤) ) = ¬a∧¬b ∧ X(¬b U b) ≡ ¬a∧¬b∧Fb     -- checked in spot
```

The single mark set `i = {0}` is hit on every move, so `GF(comp_0)` is implied
and vanishes, giving `STAY∞ ≡ G(a ∨ Fb)` — pure LTL, equivalent to the input,
where the `buchi` technique emits a 48-node blob.

Here — and *only* by a double coincidence — the unsound flat form
`G( (a∨b) ∨ (¬b U b) ) ≡ G(a ∨ Fb)` happens to give the same answer:
`petal ∨ entry = (a∨b) ∨ (¬a∧¬b) = ⊤` (the hub can never be stuck, closing the
"too loose" gap) **and** `E_s = ¬a∧¬b ⊨ ¬b = G_s` (closing the "too strict"
gap). Neither holds for a general star — see `probe_flatG_side_condition.py`,
where the flat form fails both ways. The original `probe_bigloop_Gafb.py` reads
the flat form; it is a witness for this one language, not the construction.

## Degenerate cases

- **No spokes** (`D(h) = ∅`) ⇒ `Φ = ⋁(σ ∧ XΦ) ∨ ⋁(g_j ∧ Xφ_j)`, which is daisy
  verbatim: `STAY∞ = G(σ) ∧ ⋀_i GF(σ_i)`, `LEAVE = σ U ⋁_j(g_j ∧ Xφ_j)`.
- **No petals, no stems** ⇒ pure recurrence through spokes; `G(a∨Fb)` is this.
- **A spoke that cannot return** (`R_s` unreachable from `s` under `G_s`) is not a
  spoke of this construction — its accepting divergence is `decomp/scc`'s, and
  the strong `U` in `move_s` correctly refuses to claim it.

## Open points (small, by design)

- **The exact closed `StaySafe`.** The phase recursion `(Stay_h, Stay_s)` above is
  the definition; the flat-`G` form is unsound (probe). The remaining math: its
  finite-LTL closed form (it exists — the language is star-free — but is not yet
  written), i.e. the move-level lift of daisy's `G(σ)`. This is the length-1
  instance of `algorithm.md`'s "move-level closed form" open point and the thing
  that decides whether the degenerate construction is code-ready.
- **Parallel edges on a role.** Several entries / returns / self-loops on one
  spoke, possibly with different marks: per-role disjunction is fine for the
  guards but the mark bookkeeping (which entry pairs with which return) needs a
  spec.
- **Multiple spokes, acceptance interplay.** `comp_i` is per-move; with several
  spokes carrying overlapping marks the `GF` conjunction needs a re-check that no
  cross-spoke stitching is implied (the entry-aware `StaySafe` already forbids it
  structurally — confirm on a two-spoke probe).

## The next step (fold back into `algorithm.md`)

Lift S2: let `C ∖ {h}` be a DAG of self-loops (`k > 1`). Then a detour is a
finite path through several daisy states; its finite-word language `R_d` is no
longer one `U` block, and `{R_d} ↦ Φ` is where the **opaque finite-word labeler
`Λ_f`** (and the `X̃` end-of-word boundary) of `algorithm.md` earn their keep.
S1 (hub given, no FVS) is meant to stay. Everything else here — the three-way hub
choice, `STAY∞ ∨ LEAVE`, the completion-counted acceptance, the strong-until
"must return" division of labour with `decomp/scc` — should survive the lift
unchanged, with `move_s` generalized from "one `U` block" to "one `Λ_f` label".
