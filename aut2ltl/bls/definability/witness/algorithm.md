# The non-LTL witness

When the definability gate (`bls/definability`) finds the transition monoid
non-aperiodic, the language is not LTL-definable and the cascade reports `NOT_LTL`.
A bare verdict asks the user to trust the oracle. This module produces a **witness**:
a finite object that exhibits the counting forbidding LTL, carried alongside the
`NOT_LTL` as a diagnosis complement. It is a variant of the definability decision —
same input, same oracle machinery — that on the non-aperiodic branch extracts
witness material from GAP instead of stopping at the boolean.

It produces the material; checking it is a separate concern (the witness verifier).

## The input

The same representation the gate reads: `det_generic_minimal()`, completed, then
`extract_generators` → `(gens, masks, valuations)`. The form is read for the same
reason — on a state-minimal deterministic automaton the transition monoid is faithful
to the **syntactic semigroup**, so the group it carries is the language's, not an
encoding artifact. One difference: the witness variant keeps `masks` / `valuations`
(the gate discards them as `_`), because lifting a group element back to concrete
letters needs the letter↔generator correspondence.

## What it produces — the counting family

The only thing a non-aperiodic language can do that counter-free LTL cannot is
**count modulo a period**, so non-definability is never exhibited by one ω-word that
is in (or out of) the language: membership of any single word is consistent with
some LTL formula. The obstruction is inherently a *family that toggles*. The
algebraic root is a non-trivial group inside the syntactic structure: an element `g`
of period `p > 1` (`g, g², …, gᵖ = 1` cycling). The language can tell `gⁿ` apart by
`n mod p` — that is the counting LTL cannot express.

So a witness is a counting family `(u, v, x, p)` with period `p > 1`: finite words
`u`, `v`, an ultimately-periodic tail `x`, such that membership of `u·vⁿ·x` toggles
with `n mod p`. `v` is the group element (the period), `u` reaches a state where `v`
acts with a non-trivial orbit, `x` discriminates the phases.

The family is the readable narration of an underlying proof object. Evaluating
`u·vⁿ·x` for `n = 0…p` and "seeing the pattern repeat" is **suggestive, not a
proof** — finitely many lasso evaluations cannot separate genuine period-`p`
counting from an aperiodic language that has not yet settled. The finite,
self-contained proof is the **`p`-cycle of inequivalent configurations**: `p`
pairwise-inequivalent states (residual languages) that `v` permutes in a single
`p`-cycle, with acceptance non-constant across the cycle. A permutation of order
`> 1` on a set of reachable, *distinguishable* configurations whose accept-status is
not invariant **is** non-aperiodicity, checkable directly: run `u`, iterate `v` and
watch the state cycle; run `x` from two phases and observe acceptance differ. The
lasso `u·vⁿ·x` is then merely the human-readable narration of that cycle.

The module emits the words; the verifier replays them.

## Extracting the group element from GAP

The aperiodicity oracle (`gap/aperiodic`) returns a boolean. The witness needs more,
so it drives a second, witness-only GAP script in `gap/`, alongside the aperiodicity
script. It returns:

- a non-trivial group H-class — a regular H-class that is a group, exactly what a
  non-aperiodic semigroup contains (Green's theory);
- a generator `g` of its Schützenberger group, of order `p > 1`;
- a `Factorization` of `g` over the monoid generators — a word in generator indices.

Lift: generator index `i` corresponds to letter `i` (its `valuations[i]`), so the
factorization is a finite word `v` over concrete letters. Gotcha: GAP acts on the
right; the composition order must match the image-list convention or `v` comes out
reversed — the lifted `v` is checked against the automaton before it is trusted.

## Completing the family (u, x)

From the automaton and `v`'s induced transformation:

- `u` — a word reaching a state `q` on a non-trivial `v`-orbit (`q, v(q), …`
  distinct), found by search from the initial state.
- `x` — an ultimately-periodic word separating two phases of the orbit (a tail in
  the residual of one phase and not the other). Distinguishability on the minimal
  form guarantees it exists. A real trap in constructing the family: the
  distinguishing tail cannot be a power of `v`. If `x = vᵖ` (the idempotent anchor),
  then `vⁿ·(vᵖ)^ω = v^ω` regardless of `n` and nothing toggles. The counting must
  surface as the **entry phase** into a genuinely different, phase-discriminating
  continuation.

## Scope

Verification of the produced witness is a separate concern (the witness verifier);
this module only emits the material.

Whether a completed witness upgrades a non-conclusive verdict to a proof is a
property of the object, asserted in the diagnosis, not computed here. The result
behind that assertion: a *completed* `(u, v, x)` family is a
**minimality-independent proof** — producing a concrete `x` that flips acceptance
between two phases of the `v`-orbit *is* the inequivalence proof, directly. So a
successful witness extraction upgrades a non-conclusive "hint" to a proof even above
the SAT-min threshold — exactly the regime (larger automata) where minimization is
unaffordable and conclusiveness is otherwise lost. The witness thus **extends the
conclusive regime**, and its check is self-contained (no trust in the oracle).

## Modules

- `witness.py` — the variant entry: prep the form (shared helpers), call the witness
  GAP script, lift the factorization to `v`, complete `u` / `x`, return the family.
- the witness GAP script in `gap/` — from the generator images, find a non-trivial
  group H-class and a factorization of one of its generators; print `p` and the
  factorization. A new sibling of `gap/aperiodic.py`.

## Layering

Same as the gate: above the floor, the GAP oracle, and the extractor; it imports
neither `Cascade` nor any `Translator`. The non-definable branch of the cascade gate
(`aut2cas`) carries the returned witness as a `NOT_LTL` diagnosis complement.
