# The sl algorithm

Two parts, read in order:

- **Algorithm presentation** — the pure, clean formulation we are converging on.
  This is the spec to implement, in isolation from the current code.
- **Synopsis of current code** — a code-faithful description of today's
  `reconstruction.py` engine, kept to compare against (the implementation the pure
  version will replace).

---

## Algorithm presentation

The pure formulation of core **sl** ("self-loop") backward labeling. It is written
to be read and implemented on its own terms; the synopsis below records how the
current code realizes a special-cased form of the same thing.

### Setting

Input is a **TGBA** `A = (Q, Σ, δ, q0, {F_1,…,F_m})`, `Σ = 2^AP`. An edge is
`(src, g, dst, A)` with a Boolean guard `g` (symbolic — a BDD over `AP`) and a set
`A ⊆ {1,…,m}` of the acceptance sets it belongs to. A run is accepting iff for
**every** set `i` it takes infinitely many `i`-marked edges (transition-based
generalized Büchi). `m = 0` means every infinite run is accepting.

We compute, per state `q`, an LTL formula `Final(q)` whose models are exactly the
words `A` accepts from `q`.

### The marguerite

sl applies to a state that is a **marguerite** (daisy): a singleton SCC — a center
`q` with **petals** (self-loops `q → q`) and **stems** (exits `q → dst`, `dst ≠ q`)
whose targets never reach back to `q`. Equivalently, the only cycles through `q`
are its own self-loops and the exit relation descends strictly. A whole automaton
is in scope when every state is a marguerite, i.e. it is **very-weak (1-weak)**:
every SCC is a single, possibly self-looping, state.

Split `q`'s out-edges into petals `SL(q)` and stems `EX(q)`, and abbreviate:

```
σ    = ⋁ { g : (g,A) ∈ SL(q) }                       all petal guards
σ_i  = ⋁ { g : (g,A) ∈ SL(q), i ∈ A }                petals carrying acc set i
ε    = ⋁ { g ∧ X Final(dst) : (g,dst,A) ∈ EX(q) }     the stems
```

### The labeling equation

A run from `q` either ends up staying in `q` forever, or eventually leaves.
**Stay or leave** — and the language is the union of the two:

```
Final(q)  =  STAY∞(q)  ∨  LEAVE(q)

STAY∞(q)  =  G(σ)  ∧  ⋀_{i=1..m} GF(σ_i)
LEAVE(q)  =  σ  U  ε
```

### The three moves

- **Leave** (`ε`). Take a stem: assert its guard now, `X Final(dst)` after.
  Multiple/overlapping stems are just a disjunction — nondeterminism needs no
  determinization.

- **Stay, finitely** (the left side of the `U` in `LEAVE`). Hold the boolean `σ`
  and *forget acceptance*: a finite stay takes only finitely many petals, so their
  marks cannot help (acceptance needs infinitely many). The **strong** `U` forces
  an actual exit, after which `Final(dst)` must carry acceptance.

- **Stay, infinitely** (`STAY∞`). Assert the TGBA acceptance *restricted to the
  petals*: `G(σ)` lets any petal be taken at each step (mix freely); `⋀ GF(σ_i)`
  forces, for each acc set, one of its petals infinitely often.

### Degenerate cases (no special-casing needed)

The single equation already covers the corners — this is the point of writing it
this way:

- **no stems**: `ε = false` ⇒ `LEAVE = σ U false = false` ⇒ `Final = STAY∞`.
- **a petal-unreachable acc set** `i` (`σ_i = false`): `GF(false) = false` ⇒
  `STAY∞ = false` ⇒ `Final = LEAVE` — staying cannot accept, so the run *must*
  leave; the strong `U` drops out on its own (no separate "must-leave" rule).
- **`m = 0`**: empty conjunction is `true` ⇒ `STAY∞ = G(σ)`.

### Open recursion: a fallback labeler

`Final` is defined by recursion through stems — `ε` mentions `Final(dst)`. We
leave that recursion **open**: sl is parameterized by a *labeler* `Λ`, a Translator
supplied at construction that maps a sub-automaton to an LTL label for its
language. At a stem target `dst`:

- if `dst` is a marguerite, continue with sl's own equation (`Final(dst)`);
- otherwise `dst` lies in a genuine multi-state SCC — off sl's fragment — and sl
  **delegates**: it hands the sub-automaton reachable from `dst` (that SCC together
  with its whole suffix) to `Λ`, and splices the returned formula in as `Final(dst)`.

sl is thus a **decorator** over `Λ`: it peels the very-weak envelope it can label
exactly and defers each hard core to `Λ`, which then runs on a *smaller* automaton
than the whole. The construction is sound whenever `Λ` is — a delegated label that
is exactly the language from `dst` plays the identical role to sl's own
`Final(dst)`. Taking `Λ` to be sl alone (no other engine) yields the pure
very-weak engine, which simply declines when it meets a non-marguerite.

### Why transition acceptance is essential

A single marguerite expresses `⋀_i GF(σ_i)` with a *different petal set per
acceptance set*. State-based acceptance can only mark a state as a whole
(all-or-nothing), so it could not say which petals feed which set without
splitting the state. Transition-based (TGBA) acceptance is exactly what lets one
state encode a rich generalized-Büchi condition — "a lot in a single state."

### Cost and representation

Guards (`σ`, `σ_i`, `ε`) are symbolic formulas/BDDs: **no `2^AP` enumeration** and
**no determinization**. Work and output size scale with the automaton's states and
edges, not with the alphabet.

### Well-foundedness

`Final` recurses only through stems; petals are summarized in place by the
equation and never recursed. Because stems descend strictly, the exit graph is a
**DAG** — the recursion has no infinite descent and bottoms out at marguerites
with no stems (pure `STAY∞`). With memoization each state is labeled once. A stem
into a non-marguerite is *not* recursed by sl: it is delegated to `Λ` (see above),
so it is a leaf of sl's own recursion; with no `Λ` to call, sl declines there.

### Expressivity (open)

The in-scope shape is the **nondeterministic very-weak (1-weak) TGBA**. The exact
LTL subclass it captures is left open here: the clean anchor is Gastin–Oddoux
(*very-weak alternating* automata ≡ full LTL), of which the nondeterministic
very-weak class is a strict subset; whether it coincides with a Manna–Pnueli level
is not settled in this note.

---

## Synopsis of current code

A faithful description of the **core** self-loop backward-labeling engine in
`reconstruction.py` (`reconstruct_ltl` / its inner `label`), as it stands. It is
meant to match the code as fact, so we can compare it against the presentation
above and clean the code toward it.

**Scope.** This covers ONLY core sl. It deliberately omits the two non-core seams
that the code interleaves into `label`:

- the **t2 / terminal-SCC fragment** reintegration (`scc_fragments`,
  `scc_entry_I`, `direct_scc_sync_attach`, the t2 short-circuit), and
- the **kr-under-sl** full-suffix delegation (`scc_labeler`, `_multi_scc_states`,
  `_sub_automaton_from`).

Those are rescue/composition layers bolted onto the recursion; the core algorithm
below is what runs when neither fires. The **invariant** machinery is factored
out into its own section (§4) because it is largely orthogonal to the labeling
rules — it only conjoins/threads a `G(...)` term through them.

---

## 1. Input model

The input is a **TGBA** (transition-based generalized Büchi automaton)
`A = (Q, Σ, δ, q0, {F_1, …, F_m})`:

- `Q` finite states, `q0 ∈ Q` initial;
- `Σ = 2^AP`; edges `e = (src, cond, dst, acc)` where `cond ⊆ Σ` is a Boolean
  guard (a BDD over `AP`) and `acc ⊆ {1,…,m}` is the set of acceptance sets the
  edge belongs to;
- a run is accepting iff for **every** acceptance set `i` it takes infinitely many
  edges with `i ∈ acc` (generalized Büchi, transition-based).

When `m = 0` (no acceptance sets) the code sets `treat_all_as_accepting = True`:
every infinite run is accepting. Throughout, `acc(e) = ∅` is used for every edge
in that mode.

`label(q)` returns an LTL formula whose models are exactly the words accepted by
`A` started in `q` — *on the supported fragment* (§3). Off it, it returns the
sentinel `UNSUPPORTED`, which surfaces as `LTLFormulaResult.declined`.

For a state `q` partition its outgoing edges into

- **self-loops** `SL(q) = { (g, A) : (q, g, q, A) ∈ δ }`, and
- **exits** `EX(q) = { (g, dst, A) : (q, g, dst, A) ∈ δ, dst ≠ q }`.

Write `or_self = ⋁ { g : (g,·) ∈ SL(q) }`.

---

## 2. The labeling rules — stay vs leave

This is the heart of the algorithm. Every label is a choice between **staying**
on the self-loops forever and **leaving** through an exit, and the acceptance
marking on the self-loops decides whether *staying* is even an option.

### 2.1 Leave-terms (the recursive part)

Each exit `(g, dst, A) ∈ EX(q)` becomes a **leave-term**

```
    leave(g,dst) = g ∧ X( label(dst) )           (invariants threaded in §4)
```

i.e. read a letter in `g` now, then from the next step on satisfy the
destination's language. `label(dst)` is the recursive call; note self-loops are
**not** recursive (they are summarized in place by the rules below). Let
`or_ex = ⋁ leave-terms`.

### 2.2 The rules (code lines `reconstruction.py:251–317`)

Let `touched = ⋃ { A : (g,A) ∈ SL(q) }` and `n = |touched|`.

**Rule S — pure self-loop sink** (`EX(q) = ∅`, `SL(q) ≠ ∅`). There is nowhere to
go; the only run stays forever. It is in the language iff staying is accepting:

```
    if n ≤ 1 (or treat_all):
        acc_cs = ⋁ { g : (g,A) ∈ SL(q), A ≠ ∅ }
        φ = G(or_self) ∧ GF(acc_cs)         if some self-loop is marked
        φ = G(or_self)                      if no self-loop is marked
    else (generalized Büchi):
        φ = G(or_self) ∧ ⋀_{i∈touched} GF( ⋁ { g : (g,A)∈SL(q), i∈A } )
```

`G(or_self)` says "stay forever"; each `GF(...)` says "and take an `i`-marked
self-loop infinitely often", one conjunct per acceptance set, exactly the
generalized-Büchi condition restricted to the self-loops.

**Rule L — exits present** (`EX(q) ≠ ∅`). Let
`has_acc = (∃ (g,A) ∈ SL(q): A ≠ ∅)` (or `treat_all` with `SL(q) ≠ ∅`).

- **Accepting self-loop present** (`has_acc`) — *stay OR leave*:

  ```
      stay  = G(or_self) ∧ GF(...)        (the Rule-S accepting body, single/gen)
      φ     = stay  ∨  ( or_self U or_ex )
  ```

  You may **stay** forever on the self-loops (meeting the marks i.o.), **or**
  loop on `or_self` and eventually **leave** through some exit. The leave branch
  is a *strong* `U`: leaving must actually happen.

- **No accepting self-loop** (`¬has_acc`) — *must leave*:

  ```
      φ = or_self U or_ex                  if SL(q) ≠ ∅
      φ = or_ex                            if SL(q) = ∅
  ```

  Staying forever on an unmarked self-loop is **not** accepting, so it is not an
  option: the run *must* leave, hence the strong `U` with no stay disjunct (and
  a bare disjunction of leave-terms when there is no self-loop at all).

**Rule ⊥ — dead** (`EX(q) = ∅`, `SL(q) = ∅`): `φ = false`.

### 2.3 Reading the dichotomy

The accepting bit on a self-loop is precisely the **stay-permission** bit:

| self-loop acceptance | staying forever | operator emitted |
|---|---|---|
| marked / accepting | allowed (must meet marks i.o.) | weak: `stay ∨ (or_self U or_ex)`, or `G(or_self) ∧ GF` |
| unmarked / non-accepting | forbidden | strong: `or_self U or_ex` |

This is the `U`-vs-`W` lever: an accepting self-loop yields a may-stay (`W`/`G`)
shape; a non-accepting self-loop forces a must-leave (`U`). Everything else in
core sl is plumbing around this one decision.

---

## 3. Supported fragment and well-foundedness

### 3.1 The fragment

`label` is **exact only on the very-weak (1-weak) fragment**: automata whose only
cycles are self-loops. Equivalently, every strongly connected component is a
single state (with or without a self-loop). On this fragment the per-state
language equations

```
    L(q) = ⋁_{self-loops} (stay/loop) and ⋁_{exits} g ∧ X L(dst)
```

are non-recursive *except* for the self-reference `q → q`, and that single
self-reference is resolved in closed form by the stay/leave rule (the `U`/`W`).
No `L(q)` depends on a non-self `L(dst)` that (transitively) depends back on
`L(q)`. That acyclicity is exactly what makes the rules a *definition* rather
than a circular constraint, and what makes the result exact.

### 3.2 Why the recursion terminates

`label(q)` recurses only along **exits** (`dst ≠ q`); self-loops are summarized in
place and never recurse. Consider the *exit graph* `G↑` on `Q` with an arc
`q → dst` for each exit edge. On the very-weak fragment `G↑` is a DAG: any cycle
in `G↑` would be a cycle in `A` using at least one non-self edge, i.e. a
multi-state SCC, which the fragment forbids. A DAG has no infinite descending
chain, so the mutual recursion `label` bottoms out — at sinks (Rule S) or dead
states (Rule ⊥) — after finitely many calls. Memoization in `state_formula`
makes it run in time linear in `|Q| + |δ|` (each state labeled once).

### 3.3 Enforcement off the fragment

The code never trusts the input to be very-weak; it guards termination and
soundness two independent ways, and either firing yields `UNSUPPORTED` (→
declined), never a wrong answer:

- **Static.** A pre-pass marks every state in an SCC of size ≥ 2 as a
  *bad state*; entering `label` on one returns `UNSUPPORTED` immediately. This
  rejects the multi-state SCCs the fragment excludes, before any recursion.
- **Dynamic.** A `visiting` set holds the states currently on the recursion
  stack. If `label(q)` is re-entered while `q ∈ visiting`, a non-self cycle has
  been found on this path → `UNSUPPORTED`. This is the runtime witness of the
  same condition the static pass screens for, and the backstop if the static
  characterization and the recursion ever disagree.
- **Depth cap.** `MAX_DEPTH` is a final guard against pathological inputs; hitting
  it is also `UNSUPPORTED`.

`UNSUPPORTED` is *poisoning*: any leave-term whose `label(dst)` is `UNSUPPORTED`
makes the whole state `UNSUPPORTED` (the sentinel is never wrapped into a
compound formula). So a single unsupported state anywhere in the suffix declines
the whole reconstruction — soundness by construction, never post-hoc checking.

---

## 4. The invariant layer (orthogonal)

Invariants are a separate concern threaded through the rules; they do not change
the stay/leave structure, they only *strengthen* it with a `G(...)` term and
let the edge guards be simplified.

**Downstream invariant of a state.** `I(q)` is the set of literals (`p` or `!p`)
that are constant on **all** edges reachable from `q`. As a formula
`Inv(q) = G(⋀ I(q))` (or none when `I(q) = ∅`). It expresses a safety fact that
holds for the entire suffix once `q` is reached.

The layer has two halves:

1. **Strip (once, up front).** Outgoing edge guards are simplified by
   existentially quantifying away the downstream invariants. This is sound
   *because* the walk re-adds each invariant, timed and `X`-wrapped, as it enters
   the owning state (next bullet). (The unstripped automaton is kept around only
   for the delegation seam, which is out of scope here.)

2. **Re-inject (during labeling).** When `label(q)` runs, with `cur = Inv(q)`:
   - the destination's invariant rides its leave-term:
     `leave(g,dst) = g ∧ X( label(dst) ∧ Inv(dst) )`;
   - the current invariant multiplies into the produced label: the stay body and
     the loop guard of the `U` are conjoined with `cur`
     (`stay ∧ cur`, `(or_self ∧ cur) U or_ex`, and `φ ∧ cur` for Rule S).

Net effect: each invariant is asserted exactly when (and as long as) its state is
in scope. Because it is both stripped from the guards and re-added on entry, the
language is preserved; the only purpose is smaller guards and tighter labels. The
labeling rules of §2 are stated without `cur` precisely because this layer can be
read off to the side — the only place it genuinely entangles with the core is the
t2 entry-timing, which is out of scope here.

---

## 5. Generalization — big self-loop edges (WIP / brainstorm, NOT implemented)

> This section is an immature design note, kept here so it is git-inspectable.
> It is the direction that would let core sl reach 2-cycle recurrences like
> `G(a → F b)` (currently declined → handled by the `buchi` technique).

**Idea.** A core self-loop is an edge labeled by a *letter* (a one-step Boolean
language). Generalize it to a **big self-loop edge** labeled by a guaranteed
finite-word language `R ⊆ Σ*` — a detour that leaves a state and is *guaranteed
to return*. The label of such an edge is obtained by **running sl on the detour
sub-automaton itself** (it is very-weak by assumption), giving a `U`-fragment
formula; it is then fed into the Rule-S/Rule-L machinery exactly like an ordinary
self-loop.

**Where `R` comes from (hub elimination).** In an SCC pick an accepting **hub**
`H` that is a *feedback vertex set* (every cycle passes through `H`). Removing `H`
leaves a DAG-of-self-loops; each path from `H` back to `H` is a detour. Eliminate
the non-hub states (topologically) into nested-`U` obligations and attach the
result as a big self-loop on the hub.

**Soundness condition (syntactic, on the TGBA).** Acceptance is collected along
the cycle; an internal cycle that avoids `H` must **not** carry *all* acceptance
sets — then staying inside the detour is non-accepting, so by the §2.3 lever it
is a *must-return* detour (a `*`, expressible by `U`), never an `ω` (which would
need `W`/star). A clean sufficient form: **no acceptance marks on self-loops
inside the detour**; marks on the *successor* edges of the chain are fine — they
are collected once per traversal and routed onto the folded pseudo-edge, which
**bears the union of all acceptance sets seen along the detour**.

**The two-level picture.** `*` (finite detour, must return) ↔ `U`; `ω` (infinite
recurrence at the hub) ↔ `W`/`G` + `GF`. The accepting bit selects the operator
at each level — the same dichotomy as §2.3, read one level up. Open questions:
exact mark bookkeeping for the union of sets on the pseudo-edge under generalized
Büchi; choosing `H` (minimum FVS vs. "the accepting states"); and how the big
self-loop interacts with the existing `visiting` well-foundedness guard (the fold
must break the back-edge so the recursion stays a DAG).
