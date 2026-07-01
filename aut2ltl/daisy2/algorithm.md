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

## The three simplifications

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

### S3 (this version): acceptance marks only on the links, never on the q1 loop

Restrict acceptance placement: **no acceptance mark sits on a spoke body
self-loop `G_s`** — marks live only on petals (hub self-loops) and on the *links*,
the entry `E_s` and the return `R_s`. This is checkable on the TGBA (decline
otherwise — `m = 0` / all-accepting fails it, the body-divergence regime). It is
the keystone of the construction, for two reasons (see §Acceptance):

1. **Revisit-of-`h` becomes a theorem.** A run that sits on the q1 loop forever
   then collects no mark ⇒ is non-accepting ⇒ *every accepting run takes a link
   infinitely often* ⇒ revisits `h` infinitely. So the **strong** `U` in the
   extended petal `E_s ∧ X(G_s U R_s)` is *exact* for accepting runs — "must
   return" is now forced by acceptance, not assumed. (Compare `algorithm.md` §3,
   where revisit-`h` is an assembly-provided promise; here it is earned.)
2. **Acceptance is a clean per-edge `GF` at the move boundary** — no "did the body
   loop?" subtlety, because the body carries nothing to count.

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

### Non-LTL stem children (the witness lift)

A stem child `φ_j = Λ(of(A↓dst_j))` may come back `NotLTL(w)`: the residue past the
stem is not LTL-definable, witnessed by a counting family `w = (u, v, x, p)` anchored at
`dst_j`. **If** the stem letter realizes the left quotient exactly (a letter satisfying
`g_j` enables neither a hub move nor a sibling stem), the language is not LTL either,
and daisy2 propagates the verdict (a non-LTL stem poisons the peel — absorbing, taken
before a decline), lifting `w` back to the hub. A stem fires from `h = q0` itself
(stems are hub exits, `EX(h)`), so the lift prepends a single letter — the stem guard
`g_j` — to the anchor: `w[u ↦ g_j·u]`. `v`, `x`, `p` are unchanged.

Exactness is not checked locally: the lifted result is **revalidated** against daisy2's
own input (`aut2ltl.verifier.revalidated` at the lift return) — replays → the verdict
stands; fails (nondeterministic overlapping exits: the lifted letter keeps another run
alive, so the residue is one member of a union and non-LTL-ness does not survive) →
degrades to a non-absorbing decline. The local BDD-only restoration (restrict the
prepended guard to `g_j` minus the hub moves and sibling stems) is known but not
implemented — root `TODO.md`.

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

**Acceptance `comp_i` — a per-edge `GF` anchor at the move boundary.** A TGBA run
accepts iff, for **every** acceptance set `i`, it traverses **infinitely many
`i`-marked edges**. We re-express each "set `i` infinitely often" as an LTL
`GF(comp_i)`, where `comp_i` marks the positions at which an `i`-marked edge is
taken. Under **S3** this reduction is *exact*, because:

- *revisit-`h` is forced* (S3.1): every accepting run takes a link i.o., so every
  mark that matters lies on a **finite move** — a petal, or one extended-petal
  excursion — and "an `i`-edge i.o." = "infinitely many *moves carrying `i`*
  complete". `comp_i` is therefore evaluated at the **move boundary** (the
  anchor: after a petal letter, or after a one-state detour returns), *not* at
  every position — this is the "not quite `G`, it's `GF` after each move" shape;
- *marks are only on petals and links* (S3 proper): so there is **no body case**
  — a mark is collected exactly once per move, on the petal or the link taken.

The mark sits on an **individual edge**, so `comp_i` is keyed to the marked edge,
not the role as a whole. Writing `E_s^i = ⋁{g : (g,M) ∈ entries_s, i ∈ M}` for the
disjunction of just the `i`-marked entry edges (and `R_s^i` likewise):

```
comp_i  =  ⋁_{petal (σ,M) : i∈M}  σ                       -- (P)  a marked petal edge
        ∨  ⋁_{s, marked entry}    E_s^i ∧ X(G_s U R_s)    -- (E)  a marked entry link
        ∨  ⋁_{s, marked return}   E_s ∧ X(G_s U R_s^i)    -- (R)  a marked return link
```

- **(P)** a marked petal is taken exactly when `σ` holds at a hub position — its
  own witness, as in daisy.
- **(E)/(R)** entry and return are taken once per traversal; the excursion
  `E_s ∧ X(G_s U R_s)` witnesses a completed move, narrowed to the **marked**
  sibling on the relevant link (`E_s^i` on entry, `R_s^i` on return). A run that
  rides an *unmarked* parallel link is correctly **not** credited.

`GF(comp_i)` then says an `i`-collecting move recurs forever, which under S3 is
exactly "set `i` infinitely often". With `m = 0` (no sets) the conjunction is
empty — but `m = 0` is all-accepting, which **fails S3** (`ensure_marked` would
mark the body), so that case declines rather than reaching here.

**Why per-edge, not per-role (the failure this fixes).** Collapsing a role to one
guard with a union mark is unsound on **parallel edges with non-uniform marks**.
`GF(a ∧ Xb)` is a one-spoke star whose hub has *two* entries split on `b` — only
`¬a∧b` carries the mark, `¬a∧¬b` does not. The run that rides the **unmarked**
entry forever, word `(¬a∧¬b · a)^ω`, completes a move every two steps yet never
takes a marked edge, so the language rejects it; the role-union form (`E_s = ¬a`,
mark `{0}`) wrongly accepted it (probe witness `cycle{!a&!b ; a}`). The per-edge
`E_s^i = ¬a∧b` above credits only the marked entry, and the witness is excluded.

**One caveat remains — and it is the reason for the gate.** `comp_i` is a property
of the **word**, while acceptance is existential over runs of a (possibly
nondeterministic) automaton; "`comp_i` here" must coincide with "*some* accepting
run takes an `i`-edge here". For the star this is benign per move — but the
exactness of the whole `StaySafe ∧ ⋀_i GF(comp_i)` rests on `StaySafe` being
exact, which is the **unsolved safety closed form** (next section). The acceptance
half is sound under S3; the safety half is not yet, so daisy2 keeps the Spot
validity gate (`partscc` pattern) as the net.

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

## Experimental findings — `best_daisy2` over the 40-formula survey

`daisy2` was slipped into the shipped `best` peel (`portfolio/builder.py`'s
`best_daisy2`) and run over the curated 40-formula survey with the Spot gate
traced (`DAISY2_TRACE`; driver `tests/daisy2/scan_corpus.py`). Two conclusions.

**When it validates, daisy2 is a large size win.** It peels 4 star SCCs the rest
of the portfolio reached only through the Büchi leaf or `partscc` — the motivating
example `G(p → (q U r))` collapses **86 → 7** DAG nodes — and over the corpus
`best_daisy2` matches `best` (40/40, all Spot-equivalent) at **−24 % DAG / −44 %
tree**. That payoff is the reason to finish the construction.

**But the closed form as emitted is currently UNSOUND — the Spot gate is
load-bearing, not a safety net.** 5/40 formulas hit a gate REJECT; without the
oracle the *too-loose* ones would be wrong answers. The cause is concrete: the
prototype emits the **flat-`G` `StaySafe`**
(`G(σ ∨ ⋁ E_s∧X(G_s U R_s) ∨ ⋁ G_s U R_s)`) — *exactly the form §`STAY∞` already
proved unsound ("No flat-`G` shortcut")*, never yet replaced by the phase-tracked
`(Stay_h, Stay_s)` recursion. The bench shows it failing on **natural** formulas
(not just the contrived `probe_flatG_side_condition` star), in two unsound ways
plus one incompleteness:

| formula | witness | direction | root cause |
|---|---|---|---|
| `G((!a&Xa)\|(a&X!a))` | `cycle{!a}` | too loose ⇒ **unsound** | flat-`G` hub-looseness: an in-body residual `G_s U R_s` validates a hub position with no entry |
| `G(a ↔ Xb)` | `cycle{a&!b}` | too loose **and** too tight | flat-`G` looseness + coupling |
| `GFa & GFb & G(a→X!a)` | `cycle{a&!b;!a&!b}` | too loose ⇒ **unsound** | acceptance over-credit (parallel edges, non-uniform marks) |
| `GF(a & Xb)` (probe) | `cycle{!a&!b;a}` | too loose ⇒ **unsound** | acceptance over-credit (marked vs unmarked parallel entry) |
| `G(a → Xb)` | `cycle{a&b}` | too tight ⇒ incomplete | body-divergence: a run loops in the spoke forever (accepting, since safety); strong-`U` excludes it |
| `G(a → Xb) & GFa` | `cycle{a&b}` | too tight ⇒ incomplete | body-divergence |

Reading it off:

- **Unsound (too loose)** has two sources, both already flagged as open caveats
  and now confirmed to bite on natural input: (i) the **flat-`G` `StaySafe`** the
  prototype emits in place of the `(Stay_h, Stay_s)` recursion; (ii) **acceptance
  over-credit** from collapsing parallel edges of a role into one guard with a
  union mark. These are the two real construction errors — the priority fixes.
- **Incomplete (too tight)** is the **body-divergence** boundary (§3): a run that
  stays in a spoke forever. This is by design, *not* a closed-form bug — but the
  implemented `decomp/scc` does **not** recover it either: `SccDecompose` splits
  *across* accepting SCCs and cannot crack a single SCC that diverges internally
  (confirmed — wrapping the peel pair in `SccDecompose` converted zero declines).
  Recovering it needs a dedicated handler (treat the diverging spoke as its own
  accepting component), so §3's "that's `decomp/scc`'s job" must be read with that
  caveat.

**The 40-formula set is a sufficient driver.** It already exercises every known
failure mode with a small witness, so the next iteration — replace the flat-`G`
`StaySafe` with the `(Stay_h, Stay_s)` recursion, and make acceptance per-edge —
can be built and checked against it before any larger benchmark.

## Next iteration: concrete code + test targets

Three targets, each naming the file/function to change and the witness that must
flip. Regression loop: `tests/daisy2/scan_corpus.py` (runs the corpus under
`DAISY2_TRACE`, reports per-formula `rej/err`); the unsound part is fixed when the
four *too-loose* witnesses report `rej=0`. The Spot gate stays throughout — the
goal is to make it a true safety net (never load-bearing).

### Target A — the per-edge `GF` anchor under S3  (DONE)

*Why:* `comp_i` credited a whole role (`E_s`/`G_s`/`R_s` as one disjunction with a
union mark), so a traversal taking an *unmarked* parallel edge still satisfied
`GF(comp_i)`. Witness: `GFa&GFb&G(a→X!a)` (`cycle{a&!b;!a&!b}`). S3 makes the fix
sound and drops the body case entirely (no marks on `G_s`).

*Done:*
- `shape.py`: `star_partition` enforces **S3** — declines if any spoke body
  self-loop carries a mark; `Spoke` keeps the link marks **per edge** in
  `entries/rets : List[(guard, marks)]` (aggregate `entry/body/ret` guards stay as
  the move builders).
- `daisy2.py` `build_candidate`, `comp_i`: the per-edge form — for set `i`,
  `E_s^i = ⋁{g : (g,M)∈entries_s, i∈M}` (likewise `R_s^i`): marked petal `σ`;
  marked entry `E_s^i ∧ X(G_s U R_s)`; marked return `E_s ∧ X(G_s U R_s^i)`. No
  body case.

*Result:* corpus gate-rejects 5 → 3; `GFa&GFb&G(a→X!a)` validates (`rej=0`), and
daisy2's coverage widens (it now also peels star SCCs inside conjunctions like
`G(a→Fb)&G(c→Fd)`). The Spot gate is now a true safety net for the **acceptance**
half.

*What it did NOT fix — and why that matters.* `GF(a&Xb)` still rejects
(`cycle{!a&!b;a&b}`), but not for over-credit: its marked **petal** `a&b` and a
**spoke return** read the *same letter*, so `comp_i`'s petal term fires at a spoke
position with no way to tell it is not at the hub. That is the **phase problem in
acceptance** — the marked-petal/link term needs the hub anchor exactly as
`StaySafe` does. So the remaining three corpus rejects (`G(a→Xb)`,
`G((!a&Xa)|(a&X!a))`, `G(a↔Xb)`, all `m=0`) *and* the `GF(a&Xb)` acceptance case
all reduce to the **single** missing piece: the hub anchor of Target B.

### Target B — StaySafe: the anchored fixpoint, not the flat `G`  (fixes the hub-looseness unsoundness)

*Why:* `build_candidate` emits `G(σ ∨ ⋁ E_s∧X(G_s U R_s) ∨ ⋁ G_s U R_s)`. The bare
`G_s U R_s` disjunct validates a **hub** position with no preceding entry — the
flat-`G` defect §`STAY∞` already proved. Witnesses: `G((!a&Xa)|(a&X!a))`
(`cycle{!a}`), `G(a↔Xb)` (`cycle{a&!b}`).

*Code:* `STAY∞`'s safety part is not a `G` over a position predicate; it is the
**position-0-anchored fixpoint** `Φ` of §The label,
`Φ_stay = νZ. ⋁_petals(σ∧XZ) ∨ ⋁_spokes(E_s ∧ X(G_s U (R_s ∧ XZ)))`, which
threads phase through the `X`s from `q0 = h`. Built that way a body residual is
reachable **only after its entry** `E_s` — there is *no* standalone-body disjunct,
so the hub-looseness is gone by construction. Sub-steps:
- stop wrapping a flat disjunction in `G`; build `Φ_stay` by the
  `(Stay_h, Stay_s)` recursion (hub obligation a greatest fixpoint, each spoke
  body a strong-`U` least fixpoint);
- the finite-LTL realization of that `ν`-fixpoint for a *multi-move* star is the
  open math (the macro `(Stay_h, Stay_s)` automaton is itself a length-1 star —
  self-similar); single-move stars already collapse to daisy's `G(σ)`;
- until the finite form lands, emit nothing rather than the unsound flat-`G` — the
  gate then declines (sound), instead of relying on the oracle to catch a wrong
  candidate.

*Design lead — partscc already solves this, deterministically.* `partscc`
(`aut2ltl/partscc/algorithm.md`) faces the identical "name the occupied state with
no proposition for it" problem and cracks it: the phase is **a function of the last
letter** — `L(s) = ⋁(letters entering s)`, and "in `s`" ⟺ "the previous letter
∈ `L(s)`" — and position 0 is anchored by the init state directly,
`φ = O(q0) ∧ G(⋀_s L(s) → X O(s)) ∧ ⋀_i GF(⋁_{s∈F_i} L(s))`. That **is** a flat-`G`
transition law, and it is sound *only because the `L`-partition is deterministic*
(entry letters identify the state). daisy2's open case is exactly the
**non-deterministic** star where that partition fails — `L(h) ∧ L(s) ≠ false`, the
very letter coincidence behind `GF(a&Xb)`. The lead: replace partscc's
*letter-level* determinism with **move-level self-delimitation** — each move is an
`E_s`-to-`R_s` strong-`U` block, so the anchor need not be recovered from the
letter; it **re-anchors at every `R_s ∧ X Φ`** (move completion), starting from
`q0 = h` exactly as partscc starts from `O(q0)`. Φ_stay is the same anchor,
propagated by moves instead of by a deterministic letter-partition. (Where the star
*is* L-partition-deterministic, partscc already labels it — the two are
complementary, and the portfolio orders `partscc` before `daisy2` for that reason.)

*Test:* `G((!a&Xa)|(a&X!a))` and `G(a↔Xb)` lose their too-loose witness — they may
still decline (closed form pending) but must never gate-REJECT for being *loose*.

### Target C — body-divergence stays out of scope (no daisy2 code)

`G(a→Xb)`, `G(a→Xb)&GFa` decline by design (a run loops in a spoke forever);
daisy2's strong-`U` is correct, do not patch it. It is also *not* fixed by the
current `SccDecompose` (splits across SCCs, not within one). A dedicated in-SCC
divergence handler is separate, later work.

## Working notes — findings & direction (keep)

Distilled understanding, to survive context churn:

- **The anchor is the spine.** Every open reject — the `m=0` safety cases and the
  `GF(a&Xb)` acceptance coincidence — is one problem: *name "control is at the hub"
  with no proposition for it*. Solve that and they all close. partscc is the
  deterministic shadow of the answer (last-letter `L`-partition + init anchor);
  daisy2 needs the **non-deterministic** version, with the move's strong-`U`
  providing self-delimitation so the anchor re-fires at each move completion
  (`R_s ∧ X Φ`) rather than at each letter. See Target B's design lead.

- **The strong-`U` extended petal is `Λ_f` at depth 1.** A one-state spoke's label
  is `G_s U R_s` — exactly what the general daisychain's finite-word labeler would
  return for a trivial child. So daisy2 → full daisychain is "replace the strong-`U`
  by the child's label": the *same recursion*, one rung deeper. The length-1 star is
  the base case, not a special trick.

- **S3 turns a promise into a check.** "Accepting runs revisit the hub" is, in the
  paper and `decomp/scc`, a division-of-labour *assumption*. S3 (no marks on the q1
  loop) makes it a **local edge test**: a mark-free body can't accept while
  diverging, so revisit-`h` is forced. The research move is to carve the exact
  regime and make its boundary checkable — not to handle everything.

- **Heuristic, localized.** The acceptance half is now a real construction (S3 +
  per-edge `GF`, sound by argument). The safety half is still the flat-`G`
  heuristic. The Spot gate is what makes the *whole* sound today; the goal is to
  make it a net, not a crutch — and the gap is precisely one finite-LTL fixpoint
  (`Φ_stay`).

- **A recursive composer is the next lever.** `daisy`/`daisy_pair`/`strength`/
  `acceptance`/`scc` are all `leaf(L) = combine(decompose(L), [leaf(sub)…])` with a
  floor (TODO.md `recurse`/`fix`). One `recurse(decompose, combine, floor)` is the
  single place to (a) swap `first_success → best_of` (size is the objective), (b)
  memoize on the `Language` for DAG sharing, and (c) apply `inv` **per descent**.
  Top-only `best_inv` is benchmark-neutral because the *global* `Σ = ⋁(all guards)`
  is usually `≡ true`; a deep sub-automaton has a far tighter local `Σ`. A plausible,
  testable payoff: inv-per-descent strips `G(Σ_local)`, shrinking the transition
  monoid the LTL-definability gate tests — so it may make **NOT_LTL verdicts cheaper
  or decidable** on the kinška `counting/` automata (where best currently times out).

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
