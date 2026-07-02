# The anchor algorithm

A combinator translator that labels the **initial SCC** of a state-based
ω-automaton by transcribing its transition structure onto the input word,
delegating every exit target to a child translator. It applies when the
component's **phase** — the state occupied while the run remains inside the
component — is recoverable from the word alone: each state is identified by the
letters that *move* the run into it (its **anchors**), while letters that do not
move the run (self-loop letters) may be shared freely between states. The label is
a disjunction `STAY∞ ∨ LEAVE` — stay in the component forever, accepting; or
traverse it and exit — and is **exact by construction**: no equivalence gate, no
oracle. One equation covers every regime of the component — terminal, rejecting,
accepting-with-exits, single-state — as degenerate cases, with no dispatch.

## Setting

A translator maps a language to a label; anchor is parameterized by the child `Λ`
it delegates exit targets to:

```
Label       =  Some φ  |  NotLTL(w)  |  ⊥    -- φ an LTL formula; w a non-LTL witness; ⊥ = decline
Translator  =  Language → Label
```

anchor asks the Language for its **state-based** form `A = sbacc(tgba(L))`, with
`A = (Q, Σ, δ, q0, {F_1,…,F_m})`, `Σ = 2^AP`, edges `(s, g, t) ∈ δ` carrying a
Boolean guard `g` (a BDD over `AP`), and **state-based generalized-Büchi**
acceptance: each color `F_i ⊆ Q` is a set of states, and a run accepts iff it
visits every `F_i` infinitely often (`m = 0` ⇒ every infinite run accepts).
State-based acceptance is the setting this transcription can read: it identifies
"occupying `s`" with a letter pattern, so state-level colors — visited whenever
the state is occupied, including across a self-loop stretch — transcribe directly,
whereas transition-level marks on self-loops leave no letter-visible trace.

anchor applies at the SCC `C` of the initial state `h = q0`. Being initial, `C`
has no incoming edge from outside: every reachable state descends from `h`, so an
edge back into `C` would enlarge the component. Runs therefore *start* in `C` and
each run leaves it at most once — an SCC, once left, is never re-entered. No size
is assumed: a single-state `C` is a border case that falls into line below.

## The labels

Each state `s ∈ C` carries two guard-disjunctions,

```
I(s)  =  ⋁ { g : (t, g, s) ∈ δ, t ∈ C }      -- inputs:  letters that can put the run at s
O(s)  =  ⋁ { g : (s, g, t) ∈ δ }             -- outputs: letters available from s
```

each split by whether the letter *moves* the run:

```
L(s)  =  ⋁ { g : (s, g, s) ∈ δ }                    -- Loops:   stay at s
A(s)  =  ⋁ { g : (t, g, s) ∈ δ,  t ∈ C, t ≠ s }     -- Anchors: move the run INTO s
M(s)  =  ⋁ { g : (s, g, t) ∈ δ,  t ∈ C, t ≠ s }     -- Moves:   travel onward within C
E(s)  =  { (g, d) : (s, g, d) ∈ δ,  d ∉ C }         -- Exits:   leave C toward d
```

so `I(s) = L(s) ∨ A(s)` and `O(s) = L(s) ∨ M(s) ∨ ⋁E(s)`. (The label `L(s)`
always takes a state argument; a bare `L` remains the language. The label `M` is
never used as the LTL operator `M` in this document.)

Exit guards are entirely unconstrained throughout: an exit may overlap loops,
moves, anchors, or other exits. Nondeterminism *toward an exit* is absorbed by
disjunction — each exit is one more way to accept, never a constraint on the
others.

## Step 1 — the loop-free read-off

Assume first that `C` has **no self-loops**: `L(s) = false`, so `I(s) = A(s)` and
every letter read inside `C` moves the run. Require one test:

- **P1 — anchors partition.** The `A(s)` are pairwise disjoint:
  `A(s) ∧ A(t) = false` for `s ≠ t`.

Then the phase is a function of the **last letter**: the letter that just moved
the run names its destination uniquely. LTL, which has no state, can now track the
run — each letter *promises* the next step:

```
step      =  ⋀_{s ∈ C} ( A(s) → X M(s) )                 -- the transition law, per position
fair_i    =  GF( ⋁_{s ∈ F_i} A(s) )                      -- F_i is entered infinitely often

STAY∞     =  M(h)  ∧  G step  ∧  ⋀_{i=1..m} fair_i

leave(s)  =  ⋁_{(g,d) ∈ E(s)} ( g ∧ X φ_d )              -- take an exit, child continues
LEAVE     =  leave(h)  ∨  ( M(h) ∧ ( step U ⋁_{s ∈ C} ( A(s) ∧ X leave(s) ) ) )

Final     =  STAY∞ ∨ LEAVE
```

with `φ_d = Λ(of(A↓d))` the child label of exit target `d` (`A↓d` the
sub-automaton rooted at `d`, rewrapped as a `Language` by `of(·)`).

- **The anchor at position 0.** Position 0 has no incoming letter; the input
  itself fixes the phase to `h`, so the first letter must be a move available at
  `h` — `M(h)` in `STAY∞`, an exit or `M(h)` in `LEAVE`.
- **The law chains itself.** A letter in `M(s)` lies on an actual edge `s → t`,
  hence in `A(t)` for that `t` — unique by P1 — whose own implication in `step`
  takes over. Legality comes from the consequence (`X M(s)` constrains the next
  letter to a real edge of the occupied state); identification comes from the
  trigger (P1 makes the trigger fire exactly at its target).
- **`G` versus `U`.** `step` is the *per-position* law. `STAY∞` runs it forever;
  `LEAVE` runs it only up to the final anchor — the `U` both iterates the law and
  marks where it stops applying, so the exit letter is never constrained by a law
  it is about to escape. `LEAVE`'s first disjunct is the run that exits straight
  from `h` at position 0.
- **Fairness transcribes visits.** "The run is at `s` at position `i ≥ 1`" ⟺
  "letter `i−1` fired `A(s)`"; `GF` being shift-invariant, "visit `F_i`
  infinitely often" is `GF(⋁_{s∈F_i} A(s))`.

## Step 2 — layering the loops

Now reinstate the self-loops. A letter in `L(s)` read at `s` does not move the
run, so the phase is no longer a function of the last letter — but it *is* a
function of the **last anchor**: the state entered by the last moving letter,
unchanged by the loop letters read since. That recovery needs one test beyond P1
(which now constrains only the anchors, not the full inputs):

- **P2 — loop letters never fake an anchor elsewhere.**
  `L(s) ∧ A(t) = false` for `s ≠ t`. A letter that loops somewhere is not an
  anchor anywhere *else*.

`s = t` is deliberately exempt: a letter in `L(s) ∧ A(s)` — looping at `s` and
also entering `s` from elsewhere — is harmless, since every reading of it lands
the run at `s`.

Several facts are *derived*, not assumed:

- **No stay-vs-move ambiguity.** A letter moving out of `s` lies on an edge
  `s → t` (`t ≠ s`), hence in `A(t)`; P2 already forbids it from `L(s)`. So from
  any state, loop letters and moving letters are disjoint:
  `L(s) ∧ M(s) = false` — a sojourn's end is sharp.
- **Tightness is automatic.** For `|C| ≥ 2`, strong connectivity gives every
  state a non-self in-edge inside `C`, so `A(s) ≠ false`; then `A(s) = true`
  would force every other anchor empty, a contradiction. (For `|C| = 1` all
  anchors are empty and nothing is needed.) No separate tightness test exists.
- **Machine determinism follows.** From any `s ∈ C`, a letter is a loop letter
  or an anchor into a unique target (P1 + P2 make these exclusive), so `A`
  restricted to `C` is deterministic *as a machine*. The converse fails: the
  precondition is about **transcription** — a stateless observer must recover the
  phase from the letters alone — and that is strictly stronger than determinism.
  (A letter on an edge `u → t` that also loops at an unrelated `s` leaves each
  machine step deterministic, yet is ambiguous to the observer; P2 rules exactly
  this out.)
- **Step 1's condition is strictly subsumed.** If the full inputs `I(s)` are
  pairwise disjoint, P1 and P2 hold a fortiori. The converse fails on any
  component with a shared idle letter (see the worked example).

**The phase lemma.** Under P1 + P2, at every position of a word whose run has
stayed in `C`, the occupied state is the target of the last anchor letter read,
and every letter since that anchor is a loop letter of that state. (Positions
before any anchor behave as if a *virtual anchor into `h`* were read at position
−1 — the input places the run at `h` without consuming a letter.) In past
temporal logic the phase is `L(s) S A(s)`; pure-future LTL transcribes the same
information forward: each anchor promises the **stretch** that follows it, and an
unbounded stretch of loop letters is compressed by a single `W`/`U` — bounded
formula, unbounded history.

The lemma yields a clean picture of the runs on a word `w`: within `C`, `w` has
**at most one run** (the machine is deterministic there), and every other run of
`w` is a **branch** of it — it follows the same walk and leaves through an exit
edge at some position. `STAY∞` transcribes the unique in-`C` run being infinite
and accepting; `LEAVE` transcribes some branch exiting into an accepting
continuation. Their union is everything an accepting run can do.

Each Step 1 piece generalizes by absorbing a stretch: the promised next move
`X M(s)` becomes a promised *sojourn* `X( L(s) W M(s) )`; the immediate exit
becomes loop-then-exit; fairness gains the runs that eventually stop moving.

## The label

```
sojourn(s)  =  L(s) W M(s)                                -- loop at s, then move on (or park)
step        =  ⋀_{s ∈ C} ( A(s) → X sojourn(s) )          -- the anchored transition law
park(s)     =  A(s) ∧ XG L(s)                             -- a final anchor into s, then loop forever
F_∩         =  ⋂_{i=1..m} F_i                             -- the states where parking accepts

fair        =  ⋀_{i=1..m} GF( ⋁_{s ∈ F_i} A(s) )          -- every color anchored infinitely often,
            ∨  ⋁_{s ∈ F_∩ ∩ C} F park(s)                  --   or park on a state carrying every color,
            ∨  G L(h)               (when h ∈ F_∩)        --   or park on h from position 0

STAY∞       =  sojourn(h)  ∧  G step  ∧  fair

leave(s)    =  L(s) U ⋁_{(g,d) ∈ E(s)} ( g ∧ X φ_d )      -- loop at s, then take an exit
LEAVE       =  leave(h)  ∨  ( sojourn(h) ∧ ( step U ⋁_{s ∈ C} ( A(s) ∧ X leave(s) ) ) )

Final       =  STAY∞ ∨ LEAVE
```

### The moves

- **Sojourn** (`L(s) W M(s)`). Having just anchored into `s`, the run loops on
  `s`'s own letters until a moving letter carries it onward — or forever: the
  `W`'s weak arm makes parking *legal*, and deliberately so. Whether a parked run
  *accepts* is fairness's business, not the law's — the split is what keeps every
  `U`-vs-`W` case analysis out of the law. The two arms are disjoint
  (`L(s) ∧ M(s) = false`, derived above), and the moving letter lies on an actual
  edge `s → t`, hence fires `A(t)`, whose own implication in `step` takes over:
  the law still chains itself.
- **Fairness, restructured around parking.** A run confined to `C` either moves
  infinitely often or eventually parks. If it moves infinitely often, each stay is
  finite and opened by an anchor, so "visit `F_i` infinitely often" is "anchor
  into `F_i` infinitely often" — for *every* color at once, the first disjunct.
  If it parks at `s`, the colors it visits infinitely often are exactly the
  colors of `s` — accepting iff `s` carries **every** color, i.e. `s ∈ F_∩`. So
  only `F_∩`-states need a park term; a run parking anywhere else is simply not
  accepting, and needs no formula to say so. `park(s)` is letter-exact: after
  `A(s)`, letters in `G L(s)` can fire no foreign anchor (P2), so the run
  provably never moves again. The third disjunct is `park(h)` for the virtual
  anchor — the run that never moves at all.
- **Leave.** `leave(s)` looks finitely many loop letters ahead (strong `U`), then
  asserts an exit guard now and the child label next. `LEAVE`'s first disjunct
  exits straight out of the hub's initial stretch, never anchoring; the second
  traverses — hub sojourn, law until a *last* anchor into the exiting state, then
  `leave` there.

The two branches share everything but the wrapper — one component read twice, as
a place to *live* (`G` + fairness) and as a place to *cross* (`U` to an exit).
All guards are symbolic BDDs: no `2^AP` enumeration anywhere; work and output
size scale with the states and edges of `C`, not with the alphabet.

## Degenerate cases (no special-casing)

The one equation covers every regime; no dispatch precedes it.

- **No self-loops**: `sojourn(s)` collapses to `M(s)`, `leave(s)` to the
  immediate exit, `park` and `G L(h)` to `false` — Step 1 verbatim.
- **`C` rejecting.** For state-based generalized Büchi inside one SCC, rejecting
  means some color misses `C` entirely (`F_i ∩ C = ∅` — a strongly connected
  component can cycle through any states it owns, so it accepts iff it owns a
  state of every color). Then the first `fair` disjunct contains `GF(false)` and
  `F_∩ ∩ C = ∅` empties the park terms: `fair = false`, `STAY∞ = false`, and
  `Final = LEAVE` — the traversal regime, with no rejecting-SCC test anywhere.
- **`C` terminal** (no exits): every `E(s)` is empty, `leave(s) = false`, so
  `LEAVE = false` and `Final = STAY∞` — the steady-state regime, with no
  terminality test anywhere.
- **`C` rejecting *and* terminal**: `Final = false` — correct, the component's
  language is empty.
- **`C` accepting *and* exiting**: nothing to do — both branches live, the
  component shared between them rather than split upstream and duplicated.
- **`|C| = 1`**: anchors and moves are empty, so `sojourn(h) = G L(h)`,
  `step = true`, the `U` in `LEAVE`'s second disjunct has a `false` right arm,
  and `Final = ( G L(h) when h ∈ F_∩ ) ∨ leave(h)` — loop forever on a state
  carrying every color, or loop then exit. The border case falls into line.
- **`m = 0`**: the first `fair` disjunct is an empty conjunction, `fair = true`;
  `STAY∞` is the bare anchored safety skeleton.

## Worked example

The minimal deterministic Büchi automaton for `G(a → Fb)` — state 0 accepting
("no pending obligation"), state 1 ("owe a `b`"); the fixture is
[`samples/fixtures/hoa/anchor/gafb_response.hoa`](../../samples/fixtures/hoa/anchor/gafb_response.hoa):

```
State 0 {F_1}:   [!a | b] → 0     [a & !b] → 1
State 1:         [!b]     → 1     [b]      → 0
```

One terminal SCC, `h = 0`. The full inputs **overlap**: `I(0) = !a | b` and
`I(1) = !b` share the idle letter `!a & !b` — both states wait on it — so the
Step 1 read-off declines. The anchor split:

```
L(0) = !a | b     A(0) = b          M(0) = a & !b     E(0) = ∅
L(1) = !b         A(1) = a & !b     M(1) = b          E(1) = ∅
```

P1: `A(0) ∧ A(1) = b ∧ (a & !b) = false`. P2: `L(0) ∧ A(1) = false`,
`L(1) ∧ A(0) = false`. (The exempt overlap even occurs: `L(1) ∧ A(1) = a & !b ≠
false` — read at 1 it loops at 1, read at 0 it moves to 1; either way the run is
at 1 next.) The component is terminal, so `LEAVE = false`; with `F_1 = {0}`,
`F_∩ = {0}`, the read-off is

```
Final =  ( (!a | b) W (a & !b) )                          -- hub sojourn
      ∧  G( b → X( (!a | b) W (a & !b) ) )                -- the only live step (sojourn(1) ≡ true)
      ∧  ( GF b  ∨  F( b ∧ XG(!a | b) )  ∨  G(!a | b) )   -- fair: anchor 0 i.o., or park on 0
```

— equivalent to `G(a → Fb)`; the raw read-off then passes through the shared
simplification pipeline like every other label. Note `sojourn(1) = !b W b ≡ true`:
a state whose loop letters and moves complement each other imposes no law — the
transcription is exactly as tight as the structure requires.

## Exactness

For P1 + P2 the read-off is exact — `L(A) = Final`, given correct child labels —
with no oracle. The three legs:

- **Uniqueness.** The phase lemma: within `C` a word has at most one run, and
  every run of the word is that walk or a branch of it through an exit edge.
- **Completeness.** An accepting run either stays in `C` forever or leaves it
  exactly once. Staying: its anchors and stretches satisfy `sojourn(h)` and every
  `step` trigger (a stretch letter can fire only its own state's anchor, by P2;
  an anchor letter fires exactly its target's, by P1), and its color visits fall
  into the moving-forever / parked dichotomy that `fair` transcribes. Leaving
  from the hub stretch: `leave(h)`. Leaving after at least one anchor: the prefix
  walk satisfies `step` up to the final anchor (strictly earlier sojourns end in
  genuine moves), and the final anchor-plus-`leave` is the `U`'s witness.
- **Soundness.** Conversely, the formula *forces* a run, by induction along the
  word. `sojourn(h)` (the virtual anchor's stretch) starts the run at `h`; each
  active sojourn confines the next letter to `L` of the current state (an actual
  self-loop) or `M` (an actual out-edge, entering the unique state whose anchor
  it fires, where `step`'s next trigger takes over). In `STAY∞`, each `fair`
  disjunct certifies the acceptance of *that* run: an anchor firing puts the run
  at its target, so the first disjunct yields real visits to every color when the
  run keeps moving — and if it parks at `s`, only `A(s)` can fire past the park
  (P2), so all colors anchored infinitely often forces `s ∈ F_∩`, accepting
  again; a park term pins the run on its `F_∩`-state forever. In `LEAVE`, the law
  holds strictly before the `U`'s witness position, so the final anchor is still
  constrained by the last active sojourn (it must be a legal move), and
  `leave(s)` walks actual self-loops to an actual exit edge, after which `φ_d`
  asserts the continuation lies in `L(A↓d)`. Every step is an edge of `A`; the
  assembled path *is* a run.

The argument nowhere consults whether `C` is accepting, rejecting, or terminal —
each branch is an exact transcription of one run shape, and their union is the
component's language. That is why the degeneracies above need no cases, and why
no equivalence gate is kept: under the stated preconditions — which are decided,
not guessed, by BDD tests on `C` — there is nothing left for a gate to catch. A
child's correctness is the child's own recursive responsibility, exactly as a
context-free production composes; anchor never inspects a child's formula.

## Non-LTL exit children (the witness lift)

An exit child may return `NotLTL(w)`: the residue `of(A↓d)` is not LTL-definable,
witnessed by a counting family `w` anchored at `d`. anchor propagates the verdict
(absorbing, taken before any decline) and lifts `w` to `L`'s initial state by
prepending a **reaching word** to the family's `u`: one path `h ⟶* s ⟶(g) d`
through `C`, each step's guard **restricted to the letters enabling no edge to a
different target** from its source — so the word has a single continuation at
every step and its left quotient *is* the residue (star-free, hence LTL, is
closed under left quotient; a strict-union quotient would not preserve
non-LTL-ness). The restriction subtracts *all* other-target edges, self-loops
included, so the shared loop letters that motivate anchor are already excluded
per step; parallel edges to the same target are harmless (finite-prefix marks
never touch an `Inf` set). A route whose restriction empties is skipped; if no
exact route survives, the verdict does not lift and the peel degrades to a
non-absorbing `PROBABLY_NOT_LTL` decline.

## Peers

Two portfolio neighbors remain complementary, not subsumed. The single-state peel
(`daisy`) works on the TGBA form and reads **transition-based** acceptance
directly — a per-acceptance-set petal condition (`⋀_i GF σ_i`) that the
state-based form can only express by splitting states; a recipe may well order it
before anchor, whose own single-state reading is the state-based degeneracy
above. The per-accepting-SCC union split (`sccdecomp`) remains the enabler where
anchor's precondition fails: anchor recurses down the SCC DAG through its exits,
so an anchored component needs no splitting, but a non-anchored one still does.
A genuinely shared *moving* letter (`A(s) ∧ A(t) ≠ false`, `s ≠ t`) stays out of
scope by design: the phase is then not a function of the word, and
disambiguating with a fresh proposition is not legal into LTL (projecting it out
leaves LTL for QPTL) — whether such a component can even be LTL-definable
without further structure is open.

## Literature

The precondition is a stuttering relaxation of **local automata** — automata in
which all transitions on a letter share their target, the recognizers of local
languages (Chomsky & Schützenberger 1963; Berstel & Pin 1996): erase each state's
loop letters and `C` becomes local on its anchors, while the loop letters act as
state-preserving stutter that LTL absorbs with a single `W`/`U` per stretch.
Where a local (or 1-definite — Perles, Rabin & Shamir 1963) automaton's phase is
a function of the last *letter*, anchor's is a function of the last *anchor* —
"definite modulo stuttering". The read-off itself is the local-language
characterization transcribed to ω-words: allowed first letters (the hub sojourn),
allowed digrams (`step`), and, in place of allowed final letters, the fairness of
what recurs forever.

## Out of scope (the assembly's concern)

anchor computes one local label and trusts its inputs. The child `Λ`'s
well-foundedness, the fixpoint `Λ*` closing the open recursion, first-fit
dispatch among translators, and memoization by language belong to the assembly
that wires it. Two directions are noted, not taken: **k-anchor windows** (a phase
recoverable from the last *k* anchors — `X`-chained generalizations of `step`,
the `k`-definite analogue), and relaxing the **form dependence** — the
precondition is tested on `sbacc(tgba(L))`, and an input can pass in one
automaton form and fail in another; which forms to try is a portfolio decision,
not this production's.
