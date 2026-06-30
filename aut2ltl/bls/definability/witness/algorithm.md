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
`extract_generators` → `(gens, masks, valuations)`. The form is read with the same
caveat as the gate (see the gate's **Soundness** section): on a deterministic
ω-automaton the transition monoid is **not** faithful to the syntactic ω-semigroup, so
a group it carries is only a *candidate* counting obstruction — possibly a
determinisation artefact. Turning that candidate into a proof, by completing a witness
family that separates words in the language itself, is exactly this module's job (see
Scope). One difference from the gate: the witness variant keeps `masks` / `valuations`
(the gate discards them as `_`), because lifting a group element back to concrete
letters needs the letter↔generator correspondence.

## What it produces — the counting family

The only thing a non-aperiodic language can do that counter-free LTL cannot is
**count modulo a period**, so non-definability is never exhibited by one ω-word that
is in (or out of) the language: membership of any single word is consistent with
some LTL formula. The obstruction is inherently a *family that toggles*. The
algebraic root of a *genuine* obstruction is a non-trivial group inside the syntactic
ω-semigroup: an element `g` of period `p > 1` (`g, g², …, gᵖ = 1` cycling). The
language can tell `gⁿ` apart by `n mod p` — that is the counting LTL cannot express.
(GAP finds such a group in the *transition monoid*; whether it descends to the
syntactic ω-semigroup is what completing the family decides — see The input.)

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
  the residual of one phase and not the other), found by `_distinguish` as a lasso
  accepted from one phase and rejected from the other. **It is not guaranteed to
  exist.** Unlike a minimal DFA, a state-minimal ω-automaton can keep two orbit states
  with *equal* residual ω-languages apart because the acceptance needs the memory; when
  the group is such a determinisation artefact the phases are residual-equivalent, no
  `x` separates them, and the family does not complete. **That non-completion is the
  sound signal that the group was spurious — not a bug or a timeout.** A second trap,
  when `x` *does* exist: the distinguishing tail cannot be a power of `v`. If `x = vᵖ`
  (the idempotent anchor), then `vⁿ·(vᵖ)^ω = v^ω` regardless of `n` and nothing toggles;
  the counting must surface as the **entry phase** into a genuinely different,
  phase-discriminating continuation.

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

Conversely, **failure to complete** the family — no `p`-cycle anchor, or `_distinguish`
finds the two phases residual-equivalent — means the group was a determinisation
artefact (or, at least, the count did not surface at the phases checked). This is an
*expected* outcome, not an error. Soundly, then, a non-aperiodic reading that yields no
completed witness is only a hint and should not stand as an absorbing `NOT_LTL`;
conditioning the hard verdict on a completed witness (no `x` ⇒ abstain) is tracked in
the root `TODO.md`. One honest limit on completeness: `_distinguish` compares a phase
only to its immediate successor `t[q]`, so a count that surfaces only between
*non-adjacent* phases can be missed — sound (we never assert a false proof) but not
complete (a genuine witness can go unfound). Closing that gap (compare all phase pairs)
is part of the same TODO.

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
