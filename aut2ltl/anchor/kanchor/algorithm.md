# The k-anchor algorithm (k = 2)

A combinator translator extending [anchor](../algorithm.md) — **read that first**:
its setting, the L/A/M/E labels, the child/exit machinery, and the proof
structure are all inherited, and only what changes is stated here. anchor
recovers the phase from the **last letter that moved the run**; k-anchor
recovers it from the last **k adjacent letters**, still modulo stuttering —
"k-definite modulo stuttering". This document is the k = 2 construction;
general k is a mechanical iteration noted at the end. The package is a
submodule of `aut2ltl/anchor/` — the concepts are kept separate until the
pair version demonstrably subsumes the letter version without added
complexity.

The design avoids one trap. "The last k *anchors*, with loop stretches
between them" does not work: the stretches are unbounded, so the trigger
would need `U`-nesting and the law would stop being `X`-shaped. The window
is instead over **adjacent letters**, and the stretch is absorbed by
weakening the pair's first component from `A(v)` to `I(v) = L(v) ∨ A(v)` —
any letter *consistent with the run being at `v`*, whether it just arrived
or has been looping. `I(v)` is the stutter abstraction; the window stays
rigid and the law stays `X`-shaped.

## The pair data

Everything is computed on the same `A = sbacc(tgba(L))`, initial SCC `C`,
initial state `q0`, with anchor's per-state labels `L/A/M/E` and
`I(s) = L(s) ∨ A(s)`. Two relations over `Σ × Σ` — BDDs over doubled APs
(`AP ⊎ AP′`, transition-relation style):

```
Enter₂(s)  =  ⋁ { I(v) × g : (v, g, s) ∈ δ,  v, s ∈ C,  v ≠ s }   -- pairs that move the run INTO s
Stay₂(s)   =  I(s) × L(s)                                          -- pairs that keep the run AT s
```

The doubled-AP BDDs exist **only for the precondition and drop tests
below**: the label never materializes a product — it uses `I(v)` and `g`
as separate one-letter guards under `X`.

## Preconditions

- **P1² — entering pairs partition.** `Enter₂(s) ∧ Enter₂(t) = false` for
  `s ≠ t`.
- **P2² — staying pairs never fake an entry elsewhere.**
  `Stay₂(s) ∧ Enter₂(t) = false` for `s ≠ t`.
- **P0² — the start is 0-step-anchored.** `q0`'s out-edges toward distinct
  targets have pairwise disjoint guards. Position 0 has no predecessor
  letter, so no pair exists there: the entry into the component is governed
  by the guard alone — a **0-step anchor**, the input playing the virtual
  source. This is the whole start policy of this version: the run enters
  the transcription only at position 0, only through a 0-step anchor.

`Stay₂(s) ∧ Stay₂(t) ≠ false` is allowed — that overlap *is* the stuttering
tolerance (two states waiting on shared idle pairs), resolved below by the
phase lemma. The `s = t` overlap `Stay₂(s) ∧ Enter₂(s)` is exempt exactly
like k=1's `L(s) ∧ A(s)`: either reading lands the run at `s`.

**k = 1 implies k = 2.** P1/P2 give P1²/P2² componentwise on the second
coordinate (`Enter₂(s) ⊆ Σ × A(s)`, `Stay₂(s) ⊆ Σ × L(s)`), and P0²
follows from P1 (guards into distinct targets sit in disjoint anchors) plus
P2 (loop vs. move at `q0`). So the k hierarchy is monotone: try k
incrementally and keep the smallest that passes — the k=1 label is tighter
(per-state conjuncts, one `X` less), so anchor remains the preferred
producer and kanchor fires only where it declines.

## Derived facts (the k=1 mechanism, one level up)

- **Sojourn ends stay sharp:** `L(s) ∧ M(s) = false`, re-derived. A letter
  `x` looping at `s` and moving `s → t` puts `(y, x)` in
  `Stay₂(s) ∧ Enter₂(t)` for every `y ∈ I(s)` (nonempty for `|C| ≥ 2`) —
  P2² forbids it. So `sojourn(s) = L(s) W M(s)` keeps its disjoint arms and
  is reused verbatim.
- **Move targets are unique in context:** `x` on edges `s → t` and
  `s → t'` puts `I(s) × x` in `Enter₂(t) ∧ Enter₂(t')` — P1² forbids it.
- **What k = 2 strictly gains:** a letter may loop at `v` and move
  `u → t` (`u ≠ v`) — forbidden outright by k=1's P2 — provided
  `I(v) ∧ I(u) = false`: the predecessor letter disambiguates the current
  letter's role. The phase is a function of the last *two* letters where it
  was not a function of the last one.

## The phase lemma (pairs)

Under P0² + P1² + P2², for a word whose run has stayed in `C`: any pair
`(w_{i−1}, w_i)` of the word that lies in `Enter₂(s)` puts the run **at
`s`** after position `i` — the run's actual step read that pair either as a
loop at its current state `u` (then `Stay₂(u) ∧ Enter₂(s) ≠ false` forces
`u = s`: it was already there) or as a move into some `t` (then
`Enter₂(t) ∧ Enter₂(s) ≠ false` forces `t = s`). A pair lying in no
`Enter₂` was a loop: the run is where it was. Hence the phase is the target
of the **last entering pair**, with `w₀`'s 0-step anchor standing in before
any pair has entered (and `q0` before anything at all). As at k=1, a word
has at most one run within `C` and every other run is an exit branch of it.

The lemma has a corollary the label leans on: a `step₂` trigger may fire on
a *spurious* source (`w_i ∈ I(v)` while the run sits elsewhere), but the
promise it makes is then true anyway — the pair is in `Enter₂(s)`, so the
run is at `s` regardless of which edge the trigger named. Spurious firings
are harmless, not forbidden.

## The label

anchor's letter-level pieces `sojourn(s)`, `leave(s)`, `F_all` are reused
unchanged (their soundness needed only the disjointness re-derived above).
Triggers become pairs, consequences gain one `X`, and position 0 gets the
0-step law. Conjuncts are grouped per source–target pair (`(A → C) ∧
(B → C) ≡ (A ∨ B) → C`), written per edge below for clarity:

```
enter₂(s)  =  ⋁_{(v,g,s) ∈ δ|C, v≠s} ( I(v) ∧ X g )                  -- the pair-anchor, as LTL
step₂      =  ⋀_{(v,g,s) ∈ δ|C, v≠s} ( I(v) ∧ X g  →  XX sojourn(s) )
start      =  ⋀_{(q0,g,s) ∈ δ|C, s≠q0} ( g → X sojourn(s) )          -- position 0 only, not G-wrapped

fair₂      =  ⋀_{i=1..m} GF( ⋁_{s ∈ F_i} enter₂(s) )
           ∨  ⋁_{s ∈ F_all ∩ C} F( enter₂(s) ∧ XXG L(s) )            -- park after a pair-entry
           ∨  ⋁_{(q0,g,s) ∈ δ|C, s ∈ F_all, s≠q0} ( g ∧ XG L(s) )    -- park after the 0-step entry
           ∨  [ q0 ∈ F_all ] ∧ G L(q0)                               -- park on q0 from position 0

STAY∞      =  sojourn(q0) ∧ start ∧ G step₂ ∧ fair₂

LEAVE      =  leave(q0)
           ∨  ⋁_{(q0,g,s) ∈ δ|C, s≠q0} ( g ∧ X leave(s) )            -- move at 0, exit from s's stretch
           ∨  ( sojourn(q0) ∧ start ∧
                ( step₂ U ⋁_{(v,g,s) ∈ δ|C, v≠s} ( I(v) ∧ X g ∧ XX leave(s) ) ) )

Final      =  STAY∞ ∨ LEAVE
```

### The moves

- **The law chains itself, one position of overlap.** The pair ending a
  sojourn at `s` has its first component in `I(s)` — the entering letter or
  the last loop letter — so the move out of `s` is itself the second
  component of a live `step₂` trigger. Identification comes from the pair
  (P1²/P2² make it unambiguous), legality from the consequence, exactly the
  k=1 division of labor.
- **The start.** If `w₀` moves within `C`, its target is unique by P0² and
  `start` supplies the promise `G step₂` cannot reach (the earliest pair
  constrains position 2 onward). If `w₀` loops, `sojourn(q0)` covers it and
  the eventual first move is pair-covered (its predecessor is a `q0`-loop
  letter, in `I(q0)`). Entries at position 1 are the *only* pair-less
  entries; everything later has a full window.
- **Fairness.** Moving forever: every stay is finite and opened by an
  entering pair, so color visits are `GF` of pair-entries — the single
  pair-less entry at position 1 is invisible to `GF` and harmless. Parking:
  three shapes — after a pair entry (`enter₂(s) ∧ XXG L(s)`), after the
  0-step entry (`g ∧ XG L(s)`: the run that moves at position 0 and parks
  immediately, a case the pair term cannot see), and never moving at all
  (`G L(q0)`, construction-time `q0 ∈ F_all` test as at k=1).
- **The park drop generalizes:** `Stay₂(s) ⊆ Enter₂(s)` (a doubled-AP BDD
  test) makes every park term for `s` redundant — each staying pair of the
  parked run re-fires `enter₂(s)`, so the `GF` disjunct already accepts it;
  sound only on `F_all` states, as at k=1. The same test at `q0` drops the
  `G L(q0)` disjunct.
- **`G` versus `U`, one `X` deeper.** In `LEAVE`'s traversal branch the law
  holds strictly before the witness pair, whose own `XX leave(s)` places
  the exit two positions later; the deepest reach of an *imposed* trigger
  (at witness − 1) is the final move letter, never the exit letter — the
  exit still escapes the law it is leaving. `start` joins the traversal
  branch (its reach, position 1, is strictly inside `C` there) but **not**
  the second disjunct: a run exiting from `s` at position 1 must not be
  held to `sojourn(s)`.

### The sojourn collapse (build time; retrofit to k = 1)

`sojourn(s) ≡ ⊤` whenever `L(s) ∨ M(s) = true`: at each position either a
loop or a move is legal, so `L(s) W M(s)` is a tautology — the weak arm is
what makes it one. A one-line BDD test in the builder. At k=1 this is why
`!b W b` survives in the gafb label; at k=2 it is what lets the worked
example below emit no law at all.

## Degenerate cases

anchor's regime analysis carries over verbatim — rejecting `C` empties
`fair₂`, terminal `C` empties `LEAVE`, `m = 0` trivializes the `GF`
conjunction, and no dispatch precedes the equation. Two cases are specific:

- **k = 1 passes:** the pair label is also exact but strictly larger
  (per-edge conjuncts, one more `X`); the portfolio takes anchor's label
  and kanchor is never consulted. By monotonicity this includes `|C| = 1`
  (no pairs, no start — the border case never reaches us).
- **No self-loops:** every `Stay₂` is empty, `I(s) = A(s)`, and the
  construction is the plain 2-definite (local-on-digrams) read-off, the
  loop-free layer of the k=1 document lifted one letter.

## Worked example — `GF(a ∧ Xa)`

The minimal DBA: `s0` "last letter was ¬a" (initial), `s1` "one a after a
¬a", `s2` "aa seen" (accepting, `F_1 = {s2}`):

```
State s0:        [!a] → s0     [a] → s1
State s1:        [a]  → s2     [!a] → s0
State s2 {F_1}:  [a]  → s2     [!a] → s0
```

k = 1 declines twice over: `A(s1) = A(s2) = a` (P1 fails) and
`L(s2) = a = A(s1)` (P2 fails). The pairs:

```
Enter₂(s1) = ¬a × a      Enter₂(s2) = a × a      Enter₂(s0) = a × ¬a
Stay₂(s0)  = ¬a × ¬a     Stay₂(s2)  = a × a
```

P1²/P2² pass (the exempt overlap occurs: `Stay₂(s2) = Enter₂(s2)`); P0²
passes (`s0`'s two guards are `¬a`/`a`). Every `L(s) ∨ M(s)` is `true`, so
every sojourn — including `sojourn(q0)` and all of `step₂` and `start` —
collapses to `⊤`: the component is pure liveness and the law is empty.
`fair₂`: the `GF` disjunct is `GF(I(s1) ∧ Xa) = GF(a ∧ Xa)`; the park term
for `s2` drops by `Stay₂(s2) ⊆ Enter₂(s2)`; no `q0`-edge reaches `F_all`
and `q0 ∉ F_all`, so no other park term exists. `C` is terminal, so
`LEAVE = false` and

```
Final  =  GF(a ∧ Xa)
```

— exact and minimal, with no simplifier involved.

## Exactness

The three legs of anchor's proof survive with the phase lemma swapped:

- **Uniqueness** is the pair phase lemma above.
- **Completeness.** A staying run satisfies `sojourn(q0)` and `start` (its
  position-0 step is an actual edge), and every `step₂` trigger it fires is
  true of it — genuinely (the promised edge is the one taken) or spuriously
  (the corollary: the pair still pins the run at `s`, whose actual future
  is a legal sojourn). Its color visits fall into the moving-forever /
  parked dichotomy `fair₂` transcribes, the position-1 entry covered by the
  0-step park term. A leaving run exits from `q0`'s stretch (`leave(q0)`),
  from the first stretch after a position-0 move (the second disjunct), or
  after at least one full pair — the `U`'s witness.
- **Soundness.** Induction along the word, as at k=1 but two letters at a
  time: `sojourn(q0)` and `start` root the run through position 1; each
  active sojourn confines the next letter to an actual loop or move; a move
  is the second component of a pair in exactly one `Enter₂(s)` (P1², P2²),
  where the next trigger takes over. In `STAY∞` each `fair₂` disjunct
  certifies acceptance of *that* run (a parked run's pairs are `Stay₂`
  pairs, which P2² bars from firing foreign entries — parks are still
  letter-exact). In `LEAVE` the law stops strictly before the witness and
  `leave(s)` walks actual loops to an actual exit, after which `φ_d` is the
  child's responsibility, composing as at k=1.

## Non-LTL exit children

The witness lift is anchor's, reused verbatim: the reaching-word
construction restricts each step's guard to letters enabling no edge to a
different target — a letter-level, path-local test independent of how wide
the *phase* window is — and degrades to a non-absorbing decline when no
exact route survives.

## Literature

Where anchor relaxes **local** (1-definite) automata by stuttering,
k-anchor relaxes **k-definite / k-testable** languages (Perles, Rabin &
Shamir 1963; the local-language line of Chomsky & Schützenberger 1963,
Berstel & Pin 1996): erase the loop letters and the component is
recognized by its width-2 factors; `step₂` is the allowed-trigram
constraint (`(k+1)`-factors in general), `start` the allowed-prefix
constraint, `fair₂` the ω-substitute for allowed suffixes, and `I(v)` the
stutter abstraction that keeps the window rigid over unbounded sojourns.

## Out of scope

- **General k.** `Enter_k(s)` ranges over paths of length `k−1` into `s`
  with `I`-weakened interior components; the law stays `X`-shaped
  (`I(v₁) ∧ XI(v₂) ∧ … ∧ X^{k−1}g → X^k sojourn(s)`). Cost is per-edge at
  k = 2 but per-path beyond — cap k at 2–3.
- **Uniformizing the start.** Prepending `k−1` letters of virtual history
  to `q0` (a finite entry path into a transformed automaton — a prefix a
  daisy-style peel can reabsorb) would dissolve P0² and `start` into the
  general case. An automaton surgery, secondary to the main point of
  multi-step anchors; noted, not taken.
- **Subsumption of anchor** (whether the pair label ever beats the letter
  label where both apply, and whether the packages merge) is a portfolio
  A/B question, not this production's.
- **Form dependence**, exactly as at k=1: the tests run on one automaton
  form; which forms to try is the portfolio's decision.
