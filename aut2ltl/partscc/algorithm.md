# The partscc algorithm — partition a terminal SCC

`PartScc` is a **leaf Translator**: given a `Language` whose automaton is a single
strongly-connected, escape-free component, it partitions that component by
entry-letter and emits one `G(…)` formula for "stay in it forever", validated by
language equivalence — or it declines. It is defined entirely against the
Translator contract and is **self-contained**: it asks the input for one
representation, builds a candidate, checks it, and answers. No composer has to
cooperate, and there is no entry-timing concern (see "Why a leaf" below).

> Working note. This is the spec we are converging on, written in isolation from
> the legacy heuristic (`aut2ltl/sl/heuristics/terminal_2scc.py`, the "t2" code).
> The *pure-leaf* precondition (the input being exactly one terminal SCC) is meant
> to be made reachable at the `Language` boundary, not here: `Language.of` is
> expected to grow the job of caching and Spot-minimizing each automaton as it
> comes in, so a rerooted sub-language arrives already smallified. `partscc` stays
> a strict leaf and never peeks at context to compensate; how often clean
> single-SCC inputs actually materialize is settled by test.

## Motivation

These components are **rare but real** — the `sl` experiment logs carry surviving
examples. The payoff when one fires is outsized: the emitted `φ` is a single
`G(…)` of very low complexity, dramatically smaller than what the general cascade
would produce for the same language. And because every candidate is post-validated
by equivalence, the construction is **never unsound** — at worst it declines. Low
frequency, high payoff, zero risk: that is why it earns a place beside the cascade.
It is not great yet, but it is not bad.

## Setting

The only contract surface `partscc` uses:

```
Label       =  Some φ  |  ⊥                 -- φ an LTL formula; ⊥ = decline
Translator  =  Language → Label             -- a Label also carries a technique tag
```

It asks a `Language` for its **TGBA** form `A = tgba(L) = (Q, Σ, δ, q0, F)`, edges
`(src, g, dst, A)` with a Boolean guard `g` (a BDD over `AP`). Nothing else.

## The shape it accepts

`partscc` labels `A` only when `A` is, as a whole, a **terminal accepting
component**:

- **single SCC** — `A` is strongly connected (every state reaches every state);
- **escape-free** — no edge leaves the component (trivially true when the whole
  automaton is the SCC); together with "single SCC" this means every infinite run
  stays forever, so `L(A)` is purely the steady-state ω-language;
- **size ≥ 2** — a 1-state self-loop is core sl's job, not a partition.

Anything else → `⊥` (decline). The precondition is checked, never assumed.

## The labels

For each state `s`, two disjunctions of guards:

```
L(s)  =  ⋁ { g : (·, g, s, ·) ∈ δ }         -- entry-letter label: edges INTO s
O(s)  =  ⋁ { g : (s, g, ·, ·) ∈ δ }         -- next-step label:   edges OUT of s
```

(All edges are internal here, since `A` is the whole component — so the
legacy "internal-only" caveat is automatic, not a special case.)

## The partition condition

The essence: give each state a formula that **uniquely characterizes** it — so the
letter just read identifies the state, and thereby selects that state's next-step
availability `O(s)` unambiguously. The candidate fires only when the chosen labels
`L(s)` do this:

1. every `L(s)` is strictly tighter than `true` (it actually constrains), and
2. they are **pairwise mutually exclusive**: `L(s) ∧ L(t) = false` for `s ≠ t`.

Condition 2 is the crux — pairwise disjointness *is* uniqueness: at most one
state's label holds per letter, so "which state am I in" is recoverable from the
last letter read. That is what eliminates the explicit states — the disjointness
does the input-determinization, no powerset.

`L(s) = ⋁` incoming guards is just the current *constructor* of such a labeling
(the letters that lead into `s`). The algorithm only needs *a* per-state
characteristic formula — sound (implied whenever the run is genuinely in `s`) and
pairwise-disjoint; how it is produced is a free parameter (see open questions).

## The formula

```
φ  =  G( ⋁_s ( L(s) ∧ X O(s) ) )
```

"forever: whichever entry class `L(s)` holds now, the next letter satisfies that
state's outgoing condition `O(s)`." A safety-shaped description of the steady
state.

## Soundness — verify before use

The partition pattern is a candidate *generator*, never trusted on faith. The
gate is one language-equivalence check:

```
accept φ   iff   are_equivalent( A, translate(φ) )
```

translating `φ` back with the project's standard settings. On equality, return
`Some φ` (credit `partscc`); otherwise `⊥`. A wrong guess is simply not adopted,
so `partscc` can never answer unsoundly — it only ever *adds* coverage. In the
pure-leaf framing the "isolate the SCC" step the legacy code performs is a no-op:
`A` already **is** the isolated component.

Note this gate also absorbs the **acceptance** question. The syntactic form assumes
every infinite run of the component is accepting; if the component carries a
non-trivial (generalized) Büchi condition that `G(…)` cannot express, `translate(φ)`
will not match `A` and the candidate is declined. Acceptance is thus handled by the
oracle, not by a separate syntactic rule.

## Why a leaf (no composer impact, no entry-timing)

The input language is *exactly* "stay in the component forever", so `φ` is the
whole answer — there is no prefix and no entry edge to time. Whatever led into the
component was already resolved upstream when the Language was rooted here (the
labeler hands an exit target as its own rooted sub-language); the crossing `X` is
the labeler's ordinary exit rule, applied to `partscc`'s opaque result like any
other child label. So `partscc` owns only the steady state, and the legacy
entry-timing surgery (synchronous-vs-delayed attach, the per-target entry
invariant) has nothing to attach to — it disappears with the in-place framing that
created it.

## Cleanups vs. the legacy t2

- mutual-exclusion is a **BDD test** `L(s) ∧ L(t) == ⊥`, not a string round-trip;
- no `sympy`; no initial-state-rewiring vestiges; no in-place fragment injection;
- the validated `φ` is the whole result, returnable through the normal contract
  (whether to `own_simplify` it before returning is an open choice).

## Status (v1)

Implemented: the steady-state leaf above (`partscc.py` / `labels.py`). It fires on
the **memoryless** terminal-SCC family — `G(p→Xq)` and its rerooted embeddings
(`a U G(p→Xq)`, `FG(!p|Xq)`) reconstruct to a tiny `G(…)`, equivalence-checked. It
**soundly declines the phase-dependent (alternating) family** (`G((!p∧Xp)|(p∧X!p))`,
`G(a↔Xb)`): the partition is built (labels tight + disjoint) but the equivalence
gate rejects `φ`, because `G(⋁ L(s)∧X O(s))` does not pin which phase position 0
starts in and so over-approximates the entry. These are exactly the cases the
legacy t2 rescued — but via entry-timing surgery pushed into sl.

The fix is **init-anchoring**, and it stays *inside* the leaf: the input Language
has a definite init state (the entry the labeler rooted at), which is part of the
leaf's own input — so position 0 can be pinned to the init state's outgoing role
(`φ = ⟨init disjunct at 0⟩ ∧ G(pattern)`) to recover exactness, with no composer
cooperation. The legacy only externalized this because it operated in-place on a
fragment with no well-defined init. Deferred (v2).

## Open questions (settle by test)

- **Init-anchoring (v2).** Pin position 0 to the init state to recover the
  phase-dependent family (see Status). Leaf-internal; the open part is the exact
  anchored shape and that it survives the equivalence gate on the alternating set.
- **Input reachability.** Whether clean single-terminal-SCC Languages actually
  reach us rides on the `Language.of` smallification plan above. Until it lands,
  an SCC embedded in a larger automaton simply makes the leaf decline — never
  wrong, only missed; we do not relax the contract to peek at context.
- **Label constructor.** Incoming-OR is one way to get a unique per-state
  characteristic formula. Where it fails to be pairwise-disjoint, a *better
  constructor* might still pin each state uniquely — this, not coarsening states
  into classes, is the generalization direction. A per-state label is enough, as
  long as it characterizes the state (and hence its `X`-availability) uniquely.
