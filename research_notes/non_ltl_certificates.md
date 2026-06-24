# Non-LTL Certificates

*A research note — distilling and grounding the "name the kernel" thread of `aut2ltl`.*

## 1. The problem

`aut2ltl` does not only reconstruct an LTL formula from an ω-automaton; on the
languages where no such formula exists it **decides** non-definability. A bare
`NOT_LTL` boolean is cheap to produce and almost worthless to trust: it asks the
user to believe an oracle (GAP, via an aperiodicity test) with no independently
checkable evidence. The goal of a *certificate* is to replace belief with a
finite object that anyone can verify against the automaton with a pen.

This note describes what that certificate is, why it has the shape it does, how
it is extracted from the machinery already in the pipeline, and what is built
versus still proposed.

## 2. Why a single word cannot witness non-LTL-ness

LTL-definable = first-order definable (FO[<]) = star-free = **counter-free** =
the deterministic transition monoid is **aperiodic** (group-free). The *only*
thing a non-aperiodic language can do that counter-free LTL cannot is **count
modulo a period**. So non-definability is never exhibited by one ω-word that is
in (or out of) the language: membership of any single word is consistent with
some LTL formula. The obstruction is inherently a *family* that toggles.

The algebraic root is a **non-trivial group inside the syntactic structure**: an
element `g` of period `p > 1` (`g, g², …, gᵖ = 1` cycling). The language can tell
`gⁿ` apart by `n mod p` — that is the counting LTL cannot express.

## 3. The certificate proper

### 3.1 The counting family

A non-LTL certificate is a **counting family**: a pumping triple `(u, v, x)` and
a period `p > 1` such that

```
u · vⁿ · x        flips membership in L as  n mod p.
```

`v` is the period word (the group element), `u` reaches the relevant context,
`x` is a continuation that distinguishes phases. This is a direct witness
against the ω-form of the McNaughton–Papert *non-counting* condition
(`∃N ∀n≥N : x·uⁿ·y ∈ L ⟺ x·uⁿ⁺¹·y ∈ L`): the family keeps toggling, forever.

### 3.2 The proof object is the cycle, not the sampled alternation

Evaluating `u·vⁿ·x` for `n = 0…p` and "seeing the pattern repeat" is
**suggestive, not a proof** — finitely many lasso evaluations cannot separate
genuine period-`p` counting from an aperiodic language that has not yet settled.

The finite, self-contained proof is the **`p`-cycle of inequivalent
configurations**:

> exhibit `p` pairwise-inequivalent states (residual languages) that `v`
> permutes in a single `p`-cycle, with **acceptance non-constant across the
> cycle**.

A permutation of order `> 1` on a set of reachable, *distinguishable*
configurations whose accept-status is not invariant **is** non-aperiodicity,
checkable directly: run `u`, iterate `v` and watch the state cycle; run `x` from
two phases and observe acceptance differ. The lasso `u·vⁿ·x` is then merely the
human-readable narration of that cycle.

### 3.3 The tail must be phase-sensitive

A real trap in constructing the family: the distinguishing tail cannot be a power
of `v`. If `x = vᵖ` (the idempotent anchor), then `vⁿ·(vᵖ)^ω = v^ω` regardless of
`n` and nothing toggles. The counting must surface as the **entry phase** into a
genuinely different, phase-discriminating continuation. So the load-bearing
object is precisely "*`v` cyclically permutes the entry phases, and the
continuation discriminates phases*" — i.e. §3.2 again.

## 4. Extraction — from the aperiodicity failure to `(u, v, x)`

The certificate is read off the **same** automaton the definability oracle uses
(see §5), through the existing extraction pipeline:

1. **Generators.** `extract_generators` already returns, for the deterministic
   complete automaton, one **state-transformation per concrete letter**
   (`gens`), the letter masks, and the readable valuations. These generate the
   transition monoid.
2. **Witnessing element.** The aperiodicity test (`IsAperiodicSemigroup` in GAP /
   Semigroups) is today a boolean. To witness, the false branch must instead
   return a **non-trivial group H-class** — in Green's terms, a regular H-class
   that is a group is exactly what a non-aperiodic semigroup contains — together
   with a `Factorization` of a generator of its Schützenberger group over the
   monoid generators.
3. **Lift to a word.** Since generator *i* corresponds to letter mask *i*, that
   factorization is a product of generators = a **finite word `v` over concrete
   letters**, printable via the existing letter pretty-printer. (Gotcha:
   transformation composition order — GAP acts on the right — must match the
   image-list convention, or `v` comes out reversed.)
4. **Complete the family.** `u` reaches a state where `v`'s induced map has a
   non-trivial orbit; `x` is a phase-discriminating continuation, guaranteed to
   exist by distinguishability (§5).

The raw material (steps 1, 3) is present today; steps 2 and 4 are the build.

## 5. Grounding: minimality, the sbacc trap, and conclusiveness

Two implementation facts make the transition monoid the *correct* object rather
than an approximation of the syntactic ω-semigroup:

- **Deterministic + state-minimal input.** On a minimal deterministic automaton
  every state is reachable and pairwise inequivalent, so a non-trivial
  permutation by `v` is a cycle of **genuinely distinct residual languages** —
  and distinguishability *guarantees* the separating tail `x` exists. Minimality
  is exactly what promotes a transition-monoid group into a language-level
  obstruction (closing the "the monoid may carry a group the language does not
  see" gap).

- **The sbacc trap.** The oracle must **not** run on the cascade's own
  parity+state-based-acceptance form. `sbacc` degeneralizes generalized-Büchi
  conditions (e.g. `Inf(0)&Inf(1)&Inf(2)` for `GFa & GFb & GFc`) into a
  "which mark am I waiting for" counter — a **spurious cyclic group** that reads
  non-aperiodic on a language that *is* LTL. The verdict (and therefore any
  witness) must be taken on a `sbacc`-free, generic-acceptance, minimized form.
  A witness extracted from the polluted form could exhibit the acceptance
  artifact, not a real obstruction.

**Conclusiveness.** A `not-aperiodic` reading is a proof only when taken on a
genuinely state-minimal form (below the SAT-minimization threshold); above it,
the form may be non-minimal and the verdict is a *strong hint*, since a group
can act on redundant equivalent states.

**The promotion result (why the witness is more than diagnostics).** A
*completed* `(u, v, x)` family is a **minimality-independent proof**: producing a
concrete `x` that flips acceptance between two phases of the `v`-orbit *is* the
inequivalence proof, directly. So a successful witness extraction **upgrades a
non-conclusive "hint" to a proof** even above the SAT-min threshold — exactly the
regime (larger automata) where minimization is unaffordable and conclusiveness is
otherwise lost. The witness thus *extends the conclusive regime*, and its check
is self-contained (no trust in the oracle).

## 6. Multiplicity and the atlas

- **Several independent obstructions.** A language can carry more than one group
  factor at once (parity-of-`a` *and* mod-3-of-`b`). The honest witness is then a
  **set of independent generators**, naturally read off the Krohn–Rhodes holonomy
  decomposition (which separates the group factors). Do not collapse multi-factor
  non-LTL-ness into one witness.

- **Periods in the wild.** Expect `p = 2` to dominate overwhelmingly — parity is
  the generic counting atom; cyclic groups of order ≥ 3 require deliberately
  contrived languages, and *where* they appear is itself a finding. Over an
  exhaustive census the accumulated witnesses form a **field guide to
  non-LTL-ness**: the minimal counting atoms, the periods that occur, how
  obstructions compose — the LTL/ω-regular frontier drawn *with witnesses*, not
  only counts.

- **Minimal witnesses** (shortest `v` inducing a non-trivial permutation,
  smallest separating `u`, `x`) are an optimization over the group's J-class
  structure, not a correctness concern — but they are what make the field guide
  readable rather than a pile of long lassos.

## 7. One object, two readings: witness ⇄ abstraction

The subgroup that certifies impossibility and the subgroup that yields the best
LTL **over-approximation** are the *same object*:

- **Extract** the group factor → the counting witness (why no LTL formula
  exists).
- **Collapse** the group factor (the largest aperiodic quotient of the cascade —
  drop exactly the non-aperiodic factors Krohn–Rhodes already isolates) → a sound
  LTL bound that abstracts away *only* the non-LTL-ness, touching nothing
  aperiodic.

"Residual vs production," one routine over the cascade's group factors returning
both. *(Caveat: this is a canonical **quotient**; its language image is **a**
sound over-approximation, not a unique minimal LTL hull — LTL is not closed under
arbitrary intersection.)*

**Spec repair.** Because the witness *names which counter* is the obstruction, it
names the one extra observable that would make the language definable: "not LTL
over your signals, but LTL over the enriched alphabet if you add a bit tracking
`parity-of-a`." The diagnosis and the fix are the same cycle.

## 8. Status

| Component | State |
|---|---|
| Boolean definability gate (`IsAperiodicSemigroup` on `sbacc`-free minimal form) | **built** |
| `sbacc`-free oracle form; fail-open on >5 AP / GAP error | **built** |
| `conclusive` gated on state-minimality | **built** |
| Diagnosis | **prose string today** (not yet a checkable object) |
| Witness `(u, v, x)` extraction (group H-class + factorization → word; complete the family) | `v`, `p` **stage-1 built**; `u`/`x` completion proposed |
| Promotion of non-conclusive → proof via a completed witness | **proposed** |
| Multi-factor witness sets from the holonomy decomposition | **proposed** |
| Census-scale "field guide" / definability atlas | **proposed** |

## 9. Open questions

1. **Completeness of prefix-pumping.** Does the `(u, v, x)` phase form capture
   *every* obstruction (including counting carried inside the ω-iteration, not
   just the prefix), or are there languages correctly decided `NOT_LTL` for which
   the extractor cannot synthesize a witness? "Decides but cannot always certify"
   is a strictly weaker guarantee; the linked-pair construction needs the actual
   argument, or a fallback that pumps inside the period.
2. **Canonicity for the atlas.** Minimal deterministic ω-automata are not
   canonical (no unique minimal parity automaton), so a transition-monoid
   obstruction is automaton-relative. Fine for a single witness; for census-scale
   claims about *which* periods occur, tie the obstruction taxonomy back to the
   syntactic ω-semigroup (the language invariant) before claiming canonicity.
3. **Cost of factorization.** Returning a group H-class representative and
   factorizing it over the generators is a second, opt-in GAP call on the false
   branch only — its cost relative to the cheap boolean gate needs measuring on
   the larger census cases.

## 10. Implementation: where the parts live, and what remains

The pipeline is being built bottom-up; this maps the code to the design above.

- **Definability gate (the verdict).** `aut2ltl/bls/definability/` — `tester.py`
  (`label_ltl_definable` → `(definable, conclusive)`) + `algorithm.md`. The boolean
  gate of §5/§8 on the sbacc-free minimal form. Built.
- **Witness extraction — stage 1 (`v`, `p`).**
  `aut2ltl/bls/definability/witness/` — `witness.py`
  (`extract_witness(lang)` → `Witness(p, v, factor)` or `None`) + `algorithm.md`.
  Reads the same form as the gate, keeps the letter valuations, and on the
  non-aperiodic branch lifts a group element to the period word `v`. The GAP script
  is `aut2ltl/bls/gap/witness_group.py`: build the transition semigroup, find a
  non-trivial group H-class, take a non-identity element `g`, compute its order `p`,
  and `Factorization(g)` over the generators → `RawWitness(period, factor)`. Built,
  unit-tested.
- **Membership certificate checker (suggestive tier).**
  `tests/probes/certificate/verify_smoke.py` — `member(aut, word)` (Spot
  `intersects`, every acceptance type, on the **input** automaton) and
  `verify_suggestive` (sample `u·vⁿ·x` for `n = 0…2p`, check the toggle). The
  verifier of §3.2 at the distinguishability tier: phase-sensitivity, not yet
  periodicity.
- **Tests / fixtures.** `tests/probes/witness/test_witness.py` — counter example
  `samples/fixtures/hoa/various/parity_a.hoa` (`L = a^{2k}(¬a)ᵒ`, period 2) yields a
  witness; LTL control `GFa` yields `None`.
  `tests/probes/witness/replay_certificate.py` — the end-to-end loop: extract
  `(v, p)` from GAP, lift to letters, replay `u·vⁿ·x` membership on the input
  automaton (toggles `10101` on the counter).

**What remains.**

- **Stage 2 — complete `(u, x)`** from the automaton (§4.4): `u` reaching a
  non-trivial `v`-orbit, `x` a phase-discriminating tail that is not a power of `v`
  (§3.3). Today `x` is hand-supplied in the replay.
- **Pin the GAP right-action order** (§4 gotcha) on a `p ≥ 3` case — `p = 2` hides a
  reversal (a 2-cycle equals its inverse).
- **Periodicity-proof tier** — the residual-equivalence query upgrading the
  suggestive replay to a proof (§3.2 / §5).
- **Wire the witness into the result** — carry `Witness` alongside `NOT_LTL` as a
  diagnosis complement in `aut2cas` (deferred; the gate path stays unmodified).
- **Refactor-to-share** the form-prep / GAP helpers once both paths are stable.
- The further reaches of §6/§7 — multi-factor witness sets, the field-guide atlas,
  the witness ⇄ abstraction collapse — remain as in §8.

---

*The keystone: the deepest output of the tool on a non-LTL language is neither
the rejected formula nor the boolean verdict, but the **kernel and its
witness** — the smallest carrier of the obstruction, the cycle that proves it,
and (by collapsing the same cycle) the closest LTL the language admits.*
