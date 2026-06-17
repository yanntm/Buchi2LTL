# The fuse2 rewriting (TGBA → TGBA)

`fuse2` is **not** a translator: it produces no LTL and obeys no `Translator`
contract. It is a **TGBA-to-TGBA rewriting** — a pattern-matching heuristic that
takes an automaton, looks for one specific shape (a non-accepting strongly-connected
component of exactly two states), and rewrites that component into a near-linear form
whose only cycles are self-loops.

Its purpose is **reach**, not reconstruction. A two-state cycle is not 1-weak, so the
local self-loop labeler `daisy` declines on it. `fuse2` unfolds the cycle once and
over-approximates the residual loop to `true`, trying to turn it into self-loops
`daisy` *can* label. So `fuse2` is an optional **pre-pass** an assembly may run before
`daisy`; on its own it reconstructs nothing.

> **Status: WIP / immature.** The rewrite is a **best-effort, deliberate
> over-approximation** with two distinct caveats. (1) It can add behaviours the
> original did not have, so it is **potentially unsound** — made safe only post-hoc by
> a Spot language-equivalence test (below). (2) Even when the gate accepts, it is
> **not guaranteed to linearize**: the unfolding sometimes leaves (or even enlarges)
> a multi-state component, so `daisy` may still decline on the result — harmlessly, it
> just gained nothing. The gate guarantees language preservation, never the target
> shape. It matches a single narrow shape found by experiment. Treat it as a heuristic
> enabler, not a settled construction.

## Signature

```
fuse2(A : twa_graph)  →  twa_graph | None
```

Given a TGBA `A = (Q, Σ, δ, q0, {F_1,…,F_m})` — edges `(src, g, dst, B)` with a
Boolean guard `g` (a BDD over `AP`) and acceptance marks `B` — `fuse2` returns:

* a rewritten automaton `A'` with **`L(A') = L(A)` guaranteed**, when the pattern
  matches and the gate accepts. `A'` is the *attempt* to linearize the cycle — usually
  in `daisy`'s reach (only self-loops), but not always (see Scope); or
* `None` when the pattern does not match, or the gate rejects the rewrite — a clean
  "no-op, use `A` as it was" signal to the caller.

`fuse2` never returns a non-equivalent automaton: the gate is unconditional. It makes
no promise about the *shape* of `A'` beyond language equality.

## The pattern

`fuse2` triggers on the first **non-accepting SCC `C` of exactly two states**
`C = {p, q}`. Two states strongly connected means both back-edges `p → q` and
`q → p` are present; either state may also carry a self-loop. Because `C` is
non-accepting, every accepted run that enters `C` must eventually **leave** it.

Among `p, q`, exactly one must carry the SCC's exit into accepting behaviour — an
edge to a state of an accepting SCC. Call that state the **initiator** and the other
the **satellite**:

* both states have an accepting exit → no match (ambiguous, not this shape);
* neither does → no match (no productive exit, not this shape);
* exactly one does → it is the initiator `p`, the other is the satellite `q`.

The satellite is the state whose self-loop the rewrite over-approximates.

## The rewrite

Read the loop operationally: a run bounces `p ↔ q` some **finite** number of times,
then escapes through `p`'s accepting exit. `fuse2` rewrites that into "take the first
`p → q` step, dwell at `q`, then move on" — one unfolding of the cycle, with the
dwell over-approximated:

1. **Copy everything outside `C`** unchanged: all edges with an endpoint outside
   `{p, q}`, including the initiator's exits to accepting SCCs.
2. **Drop the cycle's back-edges** inside `C`, keeping only the first transition
   `p → q` (the entry into the loop body).
3. **Splice an unfolded copy `p′` of the initiator**, carrying every initiator edge
   *except* `p → q` (its accepting exits, and its self-loop if any). Redirect the
   satellite's return edge `q → p` to `q → p′`. After the dwell the run continues as
   if it had taken `p`'s exits, with no path back into the loop.
4. **Over-approximate the dwell**: relabel the satellite's self-loop `q → q` with
   `true` (the full alphabet). This is the deliberate guess — it admits words the
   original rejected, to be caught (or not) by the gate below.

When this linearizes — the useful case — `A'` has only self-loop cycles and `daisy`
can label it. But the spliced copy `p′` can itself fall into a cycle (e.g. when the
initiator has a self-loop), leaving a multi-state component: the unfolding is a *try*,
not a guarantee. Either way the gate below is what governs correctness.

## The gate

The rewrite is an over-approximation, so on its own it is **unsound**. `fuse2`
restores soundness with a single check before `A'` is ever returned:

```
return A'   iff   are_equivalent(A, A')        -- else None
```

`are_equivalent` is a bounded Spot oracle (a decision on ω-regular languages), not on
the construction path. If it returns true the rewrite added no behaviour *on this
language* and `A'` defines `L(A)`; if it returns false (or raises) the guess is
discarded and `fuse2` reports `None`. Nothing downstream ever sees a non-equivalent
automaton.

## Scope / limits

* One shape only: a single non-accepting **two**-state SCC with exactly one accepting
  exit. Anything else is `None`.
* One component per call (the first found). Further size-2 components, if any, are
  reached only by whatever iteration the caller applies.
* The over-approximation frequently fails the gate; a `None` return is the common,
  expected outcome, not an error.
