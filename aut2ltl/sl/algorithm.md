# The sl algorithm — formalization (core, current version)

This is a faithful spec of the **core** self-loop backward-labeling engine in
`reconstruction.py` (`reconstruct_ltl` / its inner `label`). It is meant to match
the code as fact, so that we can reason about — and, where the formalization comes
out awkward, clean up — the code against it.

**Scope.** This document covers ONLY core sl. It deliberately omits the two
non-core seams that the code interleaves into `label`:

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
