# The LTL-definability decision

`label_ltl_definable(L)` reads one deterministic form of the ω-language of a
`Language` and answers whether an LTL formula defining it exists. It is not a
Translator (it emits no formula); it is the algebraic half of the definability
border the gate enforces around the kr cascade — the cascade is unsound on a
non-definable language (the holonomy decomposition still succeeds, but emits a
group component the parser reads as a reset, yielding a wrong formula), so the
question must be decided *before* the cascade builds.

The decision is **one-sided by nature**: this module's positive answer is a
theorem, its negative answer is a suspicion. The authority for rejection is the
sibling `witness/` package; the division of labour is stated precisely below.

## The input

Like every consumer of a `Language`, the tester asks for one representation and
works on that alone: `det_generic_minimal()` — the language determinized to a
deterministic generic-acceptance (Emerson–Lei) automaton, state-minimized with
Spot's SAT minimizer when small enough (best-effort, falling back to the
unminimized deterministic form). The tester completes it before extracting
generators; completion only adds a sink, an idempotent, so it cannot create or
destroy a group and the aperiodicity verdict is unaffected.

## The characterization

For ω-regular languages the classical equivalences hold (Thomas 1979; Perrin
1984; Perrin–Pin, *Infinite Words*, ch. on first-order logic; Diekert–Gastin,
*First-order definable languages*, 2008):

```
LTL-definable  =  FO[<]-definable  =  star-free  =  syntactic ω-semigroup aperiodic
```

**Aperiodic = group-free**: no element `g` has a non-trivial cyclic orbit
`g, g², …, gᵖ = g^{p+q}` with period `p > 1`. A non-trivial group is exactly the
ability to count modulo `p`, which counter-free LTL cannot express.

The invariant object is the **syntactic ω-semigroup** `S(L)` (Arnold 1985). It
is not what this module computes: the computable handle is the **transition
monoid** `TM(D)` of the deterministic form `D` — the transformations the letters
induce on states, which depend only on the transition function, never on the
acceptance. The oracle is `gap/aperiodic.is_aperiodic_gens` (build the
transformation semigroup from the generator images, ask GAP `IsAperiodicSemigroup`
— the cheap boolean, no holonomy). This package owns the policy around that call;
the GAP script stays in `gap/`, the Spot→generators extraction in `extract.py`
(both shared with the cascade's holonomy).

## Soundness: what the aperiodicity of `TM(D)` proves

**Positive direction — `TM(D)` aperiodic ⟹ `L` is LTL. A theorem.**
A counter-free deterministic automaton whose acceptance depends only on the set
of transitions taken infinitely often recognizes a star-free language (Thomas
1979, *Star-free regular sets of ω-sequences*; Diekert–Gastin 2008, Thm. on
counter-free deterministic Muller automata). Generic (Emerson–Lei) acceptance is
a Boolean over `Inf`/`Fin` of transition sets, hence a function of the inf-set,
hence reducible to a Muller condition; moving it to states (state = last
transition taken) preserves counter-freeness, since for `|w| ≥ 1` the enriched
action of `w` factors through the original action and a fixed suffix of `w`. The
theorem needs neither state-minimality nor any canonicity of `D`.

**A warning on the tempting converse argument.** On *finite* words the minimal
DFA's transition monoid *is* the syntactic monoid (states are the Myhill–Nerode
residuals), so aperiodicity of the one is aperiodicity of the other
(Schützenberger 1965; McNaughton–Papert 1971). No analogue holds on ω-words —
and in particular the plausible-looking claim "words with equal state action are
interchangeable in every context, so `S(L)` is a quotient of `TM(D)`" is
**false**: acceptance reads the marks visited *along* the run, not only the
endpoints, so two words with the same state map but different intermediate
visits can be separated by an ω-power context (`x·u^ω` vs `x·v^ω` may have
different inf-sets). `S(L)` can be strictly finer than `TM(D)`; no quotient
relation holds in either direction in general.

**Negative direction — `TM(D)` has a group ⇏ `L` is not LTL.** The group can be
an artefact of the deterministic encoding, and **minimization does not close the
gap**, for two independent reasons:

1. *Residual-equal states need not be mergeable.* An ω-automaton's states are
   memory for the acceptance, not only for the residual language; merging two
   states with equal residuals can destroy the inf-set structure the condition
   reads. Prefix-independent languages are the extreme case: every state of
   every deterministic recognizer has residual exactly `L`, yet more than one
   state is needed whenever `L` is not a Boolean combination of
   "letter occurs infinitely often" constraints.
2. *Minimum-size deterministic ω-automata are not canonical.* Minimization is
   NP-hard and minima are not isomorphic (Schewe 2010); a SAT minimizer returns
   *one* minimum-size model, with no preference for a counter-free one.

Both failures are realized at size 2 on one atomic proposition:
`GF(a ∧ Xa)` — star-free, prefix-independent — has two non-isomorphic 2-state
deterministic Büchi recognizers: the *last-letter* encoding (aperiodic) and the
*run-parity* encoding, whose letter `a` is a transposition (a `Z2` group in
`TM`). The two mark different transition sets on every run yet agree in the
limit — modular counts collapse to thresholds at infinity (`Σ⌊kᵢ/2⌋ = ∞ ⟺
kᵢ ≥ 2 infinitely often`). Fixtures:
`samples/fixtures/hoa/definability/gf_aa.hoa` / `gf_aa_parity.hoa`.

Hence a non-aperiodic reading is a **suspicion at any size**, minimal or not.
Promoting it to a verdict is the witness's job.

## The verdict pair

```
label_ltl_definable(L)  →  (definable, conclusive)        definable ∈ {True, False, None}
```

- `definable = True` — `TM(D)` is aperiodic. **A proof** that `L` is LTL
  (positive direction above); the gate delegates to the cascade.
- `definable = False` — `TM(D)` carries a group. **A suspicion only.** The gate
  hands it to `witness/` for certification; the outcome is decided there:
  - a **certified** counting family (completed *and* replayed against the input)
    yields the absorbing `NOT_LTL` — a proof independent of this module;
  - no certified family yields a **non-absorbing** `PROBABLY_NOT_LTL` decline:
    the cascade is never built on the suspect language (it is unsound there),
    but no verdict is asserted and other translators — each sound by
    construction, faithful-or-decline — remain free to answer. A wrong absorbing
    rejection is thereby impossible; the cost of a spurious group is bounded by
    the loss of the cascade on that input.
- `definable = None` — the oracle **could not run** (too many APs for a
  tractable letter set, a GAP error/timeout). Nothing was read in either
  direction. The gate treats it exactly as an uncertified suspicion — a
  non-absorbing decline, the cascade never built — with its own reason and no
  `PROBABLY_NOT_LTL` marker (no group was read, so no suspicion is asserted).
  One fence for everything the gate cannot certify: the cascade builds **only**
  behind a proved-aperiodic reading, by construction — never on the hope that
  whatever blocked the oracle would block the cascade too (the two share
  machinery today, but soundness must not rest on an implementation quirk).
- `conclusive` — whether the form was actually SAT-minimized (`n ≤` the
  threshold). It grades the *diagnosis prose* only. It is **not** proof-grade
  for rejection — see the negative direction: the `GF(a ∧ Xa)` run-parity form
  is minimal, `conclusive` would read true, and the language is LTL.

## Why generic acceptance, not the cascade's state-based form (`sbacc`)

The cascade builds from `det_parity_sbacc()`, which the tester must not reuse.
Forcing state-based acceptance degeneralizes a generalized-Büchi condition
(e.g. `Inf(0)∧Inf(1)∧Inf(2)` for `GFa ∧ GFb ∧ GFc`) by adding a round-robin
"which mark am I waiting for" index. That index is a cyclic group in the
transition monoid — an artefact of the acceptance *encoding*, not of the
language — so it reads as non-aperiodic even when the language is LTL. The
generic-acceptance form carries no such counter; it removes *this* artefact
(though, per the negative direction, not every encoding artefact).

## When the oracle cannot run

When the oracle cannot run at all — too many APs to extract a tractable letter
set, or a GAP error/timeout — the tester returns `(definable=None,
conclusive=False)`: it fabricates neither a rejection nor a definability claim.
The gate's fence is then the same as for an uncertified suspicion (decline,
never build), differing only in the stated reason. The invariant this buys is
simple and implementation-independent: **the cascade builds only behind a
proved-aperiodic reading** — there is no path on which it runs unvouched-for.

## Caching

The verdict is computed once per `Language` and tagged via `set_ltl_definable`;
a cached pair short-circuits the call. The gate is the single choke point for
all cascade members — each runs only after it — so one GAP call serves the whole
portfolio pass over a Language.

## Modules

- `tester.py` — `label_ltl_definable`: pull `det_generic_minimal()`, record
  `conclusive` from the SAT-min threshold, complete and extract generators, run
  the aperiodicity oracle, abstain on error, cache the pair.

## Layering

Sits above the floor (reads `Language`, `SAT_MIN_STATES`) and above the GAP
oracle (`gap/aperiodic`) and the extractor (`extract`). It imports neither
`Cascade` nor any `Translator`, so it composes into the cascade gate without a
cycle. Consumer: the gate (`../gate.py`).

> Forward note: on the suspect branch the same transition-monoid group that
> fails aperiodicity is the carrier of the witness material — the counting
> families that, once certified, prove non-LTL-ness. Extraction, completion and
> certification are owned by the sibling `witness/` package; see
> `witness/algorithm.md`.
