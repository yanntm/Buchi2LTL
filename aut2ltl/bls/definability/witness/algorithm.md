# The non-LTL witness

When the definability tester reads a non-aperiodic transition monoid, the
language is *suspected* not LTL-definable — a suspicion only, since the group
may be an artefact of the deterministic encoding (see the tester's
**Soundness**). This module owns the object that settles it: a **counting
family**, a finite, representation-independent certificate that the language
counts modulo a period, which no counter-free LTL formula can do. The gate
asserts the absorbing `NOT_LTL` **only** on a family this machinery has
completed *and* certified by replay; a suspicion that yields no certified family
is surrendered as a non-absorbing `PROBABLY_NOT_LTL`.

Producing the material is this module's concern; replaying it against an
automaton is the verifier's (`aut2ltl/verifier`). The two are kept separate so
the certificate never depends on the form it was discovered on.

## The certificate: counting families, two shapes

Non-definability is never exhibited by a single ω-word — membership of one word
is consistent with some LTL formula. The obstruction is inherently a *family
that toggles*. Two shapes are needed, and two suffice:

```
linear    F₁(u, v, x, p) :  n ↦ [ u·vⁿ·x ∈ L ]        toggles with n mod p
ω-power   F₂(u, v, y, p) :  n ↦ [ u·(vⁿ·y)^ω ∈ L ]     toggles with n mod p
```

with `p > 1`, `u`, `v`, `y` finite words, `x` an ultimately-periodic ω-word
(a lasso), all over the shared alphabet `Σ = 2^AP`. "Toggles with `n mod p`"
means: the membership function is determined by `n mod p` for **all** `n ≥ 0`
and is not constant. Every sample of either shape is an ultimately-periodic
word, so both shapes are checkable by membership queries alone.

**Soundness (either shape completed ⟹ `L` is not LTL).** If `L` were star-free
its syntactic ω-semigroup would be aperiodic (Perrin 1984; Perrin–Pin, *Infinite
Words*), so `[vⁿ]` would be eventually constant in `n`, making both membership
functions eventually constant — contradicting a genuine period `p > 1` holding
for all `n`. The proof is independent of any automaton, of minimality, and of
the oracle that suggested `v`.

**Completeness of the pair (why two shapes, and why no third).** The syntactic
congruence of an ω-regular language (Arnold 1985) separates two words by exactly
two context shapes: a linear context `x·_·y·t^ω` and an ω-power context
`x·(_·y)^ω`. If `L` is genuinely not star-free, some `[v]` has a cycle of period
`p > 1` in `S(L)`, and two of its powers are separated by a context of one of
the two shapes; unrolling that separation along the cycle yields a toggling
family of the corresponding shape. Hence: **`L` not LTL ⟺ a family of shape F₁
or F₂ exists.** No further shape is ever required.

**The linear shape alone is not enough — a blindness lemma.** If `L` is
prefix-independent (`σw ∈ L ⟺ w ∈ L` for every finite `σ`), then
`u·vⁿ·x ∈ L ⟺ x ∈ L`: every linear family is constant, on every choice of
`(u, v, x)`. Equivalently, all reachable states of any deterministic recognizer
have residual exactly `L`, so no tail can separate any two of them.
Prefix-independent non-LTL languages exist — e.g. *"infinitely many `¬a` and
eventually every `a`-block has even length"*
(`samples/fixtures/hoa/definability/evenblocks_nonltl.hoa`), whose count is exhibited
by the ω-power family `(aⁿ·¬a)^ω` and by no linear one. The ω-power shape is a
requirement, not an optimization.

## Extraction

The module reads the same form as the tester (`det_generic_minimal()`,
completed) and keeps what the tester discards: `masks` / `valuations`, the
letter↔generator correspondence needed to lift group elements back to concrete
letters.

### The group element (shared root of both shapes)

The aperiodicity oracle returns a boolean; the witness drives a second,
witness-only GAP script (`gap/`) that returns a non-trivial group H-class of the
transition monoid (Green's theory: what a non-aperiodic semigroup contains), a
generator `g` of its Schützenberger group with order `p > 1`, and a
`Factorization` of `g` over the monoid generators. Generator index `i`
corresponds to letter `valuations[i]`, so the factorization lifts to a concrete
word `v`. Gotcha: GAP acts on the right; the composition order must match the
image-list convention or `v` comes out reversed — the lifted `v` is re-checked
against the automaton (its induced transformation is recomputed concretely)
before anything is built on it.

### Completing the linear shape (u, x)

From `v`'s induced transformation `t` on the states of `D`:

- **anchor** — a state `q` on a `t`-orbit that **closes** with length exactly
  `p` (`q, t(q), …, t^p(q) = q`, all distinct). Closure is mandatory: a spiral —
  a transient leading into a shorter cycle — proves nothing, and its replay
  signature (one accepting sample, then constant) must never reach the gate.
  **All** orbits of length `p` are candidate anchors, not the first found: a
  genuine count may separate on one orbit and not another.
- **reach** — `u`: a shortest word from the initial state to `q` (BFS over the
  letter generators).
- **separate** — `x`: a lasso accepted from one orbit phase and rejected from
  another, found per pair via `product(Dᵢ, complement(Dⱼ)).accepting_word()`.
  **All** phase pairs `(i, j)`, `0 ≤ i < j < p`, are tried — a count can surface
  between non-adjacent phases only; comparing a phase solely to its successor is
  sound but incomplete. A separator found between phases `i` and `j` yields a
  family of period `p' = p / gcd(p, j−i) > 1` — the family's declared period is
  the toggling period, not necessarily the group order. Trap: `x` must not be a
  power of `v` (then `vⁿ·(vᵖ)^ω = v^ω` for every `n` and nothing toggles); the
  discriminating tail must enter a genuinely phase-distinguishing continuation.

### Completing the ω-power shape (u, y)

The linear search fails precisely when the orbit phases are residual-equal —
where the count, if genuine, lives in the *acceptance along the loop*, which the
transition monoid forgets. The right candidate space restores that information:
the **acceptance-enriched monoid** of `D`, whose element for a word `w` maps
`q ↦ (δ(q, w), marks collected from q along w)`. It composes as
`(f, M)·(g, N) : q ↦ (g(f(q)), M(q) ∪ N(f(q)))`, i.e. it *is* a transformation
monoid on the finite set `Q × 2^C` (`C` the acceptance marks) — directly
GAP-representable, letters as generators.

Completion: anchor `u`, `q` and the orbit as in the linear shape; then search
for a **return word** `y` such that the lasso `(vⁿ·y)^ω` read from `q` is
accepted for some `n` and rejected for another, `n < p`. Two facts bound the
search:

- membership of `u·(vⁿ·y)^ω` for each candidate is one lasso-membership query —
  cheap and exact;
- `y` matters only through its enriched-monoid element, of which there are
  finitely many; BFS over the enriched monoid enumerates one shortest concrete
  representative per element, so the search is exhaustive in bounded (if
  potentially large) time.

**Exhaustion is meaningful.** If a family of either shape exists as words, its
components act on `D` only through their (enriched) transformations, so a
representative-per-element search realizes one — this *candidate-sufficiency*
argument is what upgrades "nothing found" from a shrug to a signal: after a
genuinely exhaustive both-shape search, the group is an encoding artefact and
the language is star-free. (The dual certificate closes the same gap from the
other side: exhibiting *any* counter-free deterministic recognizer of the same
language proves star-freeness outright — Thomas 1979. The run-parity/last-letter
pair `gf_aa_parity.hoa` / `gf_aa.hoa` is the minimal instance of both routes.)
Bounded implementations truncate this ideal; a truncated search that found
nothing still only ever yields the non-absorbing `PROBABLY_NOT_LTL`, never a
verdict, so the truncation costs completeness, not soundness.

## Certification (the gate's contract)

A completed family is **material**, not yet a verdict. Before the gate absorbs:

- **replay**: the family is replayed by membership against the *input*
  automaton (the verifier, in-process, bounded) — sampling `n = 0 … 2p` and
  checking the pattern is `p`-periodic and non-constant. Given closure was
  computed concretely at extraction, the sampled toggle certifies the family;
  the replay's role is to catch transport corruption between the discovery form
  and the input (wrong lift order, letter mismatches, an invalid peel lift). A
  family that fails replay is discarded as if never completed.
- **trust tiers**: no replay — zero (the family is decoration); replayed —
  proof-grade, resting on concrete orbit closure plus uncorrupted transport. A
  zero-trust tier needing no faith in extraction exists if ever required: the
  checker determinizes the input itself and samples `n` up to its own
  stabilization bound (`lag + lcm(ρ, p)` for the state sequence after `u·vⁿ`),
  making the periodicity a theorem from membership queries alone.

## Lifting a family across a peel or decomposition

A family produced below a decomposing translator describes a *sub*-language;
it certifies the composed language only under an exactness condition, owned by
the lifting translator:

- **peel (prefix consumption)**: prepending the consumed word to `u` is sound
  iff the consumed step is the run's only continuation — the peeled residue must
  equal the left quotient (e.g. a daisy stem letter enabling neither a petal nor
  a sibling stem). Star-free languages are closed under left quotient, so under
  exactness both the verdict and the family lift. Without exactness the residue
  is a strict member of a union and *neither* lifts: non-LTL-ness does not
  survive union. A peeler that cannot establish exactness (a nondeterministic
  overlap) must either determinize the local structure first and re-check, or
  decline to lift.
- **any lift**: the lifted family must be **re-replayed against the lifting
  translator's own input**. A family that was true of the part and is not true
  of the whole (the acceptance-split case: a sub-automaton family constant on
  the intersection) is caught here and degrades the result to
  `PROBABLY_NOT_LTL`. Replay-after-lift is not optional; it is what makes the
  lift rule enforceable rather than trusted.

## Scope

The family is the readable narration of an underlying proof object — the closed
`p`-cycle of configurations with a phase-discriminating continuation. A
*certified* family is a **minimality-independent, representation-independent
proof**: it extends the conclusive regime above any SAT-min threshold, and its
check is self-contained (no trust in GAP, in minimization, or in this module).
Failure to certify, after the exhaustive both-shape search, is the sound
"encoding artefact" signal and must surface as abstention — never as a verdict
in either direction, and never as a formula built by the cascade.

## Modules

- `witness.py` — the entry: prep the shared form, drive the witness GAP script,
  lift and re-check `v`, complete the linear shape (all orbits × all phase
  pairs), complete the ω-power shape (enriched-monoid candidates), return the
  family.
- the witness GAP script in `gap/` — group H-class, generator, order,
  factorization.
- `aut2ltl/witness.py` (floor) — the `Witness` value: both shapes, serialization
  (`p`, `u`, `v`, and `x=[…cycle{…}]` for F₁ / `y=[…]` loop form for F₂),
  parsing, and the peel `prepend`.

## Layering

Same as the tester: above the floor, the GAP oracle, and the extractor; imports
neither `Cascade` nor any `Translator`. The gate composes tester, witness and
the in-process replay; decomposing translators own their lift conditions.
