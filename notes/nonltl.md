# Non-LTL verdict: soundness of the rejection branch

> Untracked working note (like `tracing_spot_inproc.md`) — context + pointers for the
> open TODO "condition the hard NOT_LTL verdict on a completed witness". Not a committed
> artifact; the durable conclusions are already folded into the two `algorithm.md` docs.

## The one-line problem

The definability gate can emit a hard, absorbing, "proof"-labelled `NOT_LTL` for a
language that **is** LTL-definable. The algebraic test it uses is sound in one direction
only, and the organ that would close the gap (the witness) is currently wired as
decoration, not as the authority.

## The math (why rejection is one-way)

The gate reads the **transition monoid** `TM` of `det_generic_minimal()` and asks GAP
whether it is aperiodic. `TM` depends only on the transition function, not the
acceptance.

- For any deterministic automaton recognising `L`, two words acting identically on all
  states are interchangeable in every context ⇒ the **syntactic ω-semigroup `S` is a
  quotient of `TM`**.
- Aperiodicity passes through a quotient one way:
  - **`TM` aperiodic ⟹ `L` is LTL** (quotient of aperiodic is aperiodic ⟹ `S` aperiodic
    ⟹ star-free = FO[<] = LTL). A real proof. ✔ sound positive.
  - **`TM` has a group ⇏ `L` not LTL.** The group can live in `TM` and die in `S`.

Finite-word intuition does *not* transfer: a minimal DFA's `TM` **is** the syntactic
monoid (states = Myhill–Nerode residual classes), but a **state-minimal ω-automaton can
keep two states with equal residual ω-languages apart** because the Muller/parity
acceptance needs the memory. A `v` permuting such equal-residual states is a
determinisation artefact — a *spurious group* — not language counting. SAT-minimisation
and the generic-acceptance form kill *some* artefacts (the sbacc counter; redundant
states above the threshold) but are **not** known to kill all.

Refs: McNaughton–Papert / Schützenberger (finite words); Thomas, Perrin–Pin (ω, syntactic
ω-semigroup aperiodic ⟺ star-free ⟺ FO ⟺ LTL).

## What the witness adds (the real proof)

`witness/` extracts the GAP group element `v` (period `p>1`), then *completes* a counting
family `(u, v, x)`:
- `u` reaches a state `q` on a genuine `v`-orbit of length `p`;
- `x` is a lasso (ultimately-periodic ω-word) **accepted from one phase, rejected from
  another** — i.e. it witnesses that the orbit phases have *distinct residual
  ω-languages*.

If such an `x` exists, then `n ↦ [u·vⁿ·x ∈ L]` is genuinely periodic (the state literally
cycles) and non-constant ⇒ `L` counts mod `p' > 1` ⇒ **not star-free**. This is a
**minimality-independent proof** (no trust in SAT-min or in the oracle), valid even above
the SAT-min threshold.

Crucially: for a **spurious** group the phases are residual-equivalent, **no `x` exists**,
and the family does **not** complete. That non-completion is the sound "this was an
artefact ⇒ abstain" signal — exactly the discriminator we are failing to act on.

## Where it lives (code map)

- `aut2ltl/bls/definability/gate.py` — the consumer. `gated()` (≈L87) does
  `definable, conclusive = label_ltl_definable(...)`; on `not definable` it returns
  `LTLResult.not_definable(_explain(conclusive), witness=...)`. **L85 comment:** "failure
  to extract it never disturbs the (already decided) NOT_LTL verdict." ← the gap.
- `aut2ltl/bls/definability/tester/` — `label_ltl_definable` (aperiodicity + SAT-min →
  `(definable, conclusive)`). Boolean oracle: `gap/aperiodic.is_aperiodic_gens`.
- `aut2ltl/bls/definability/witness/witness.py` — `extract_witness(..., complete=True)`:
  - `_complete_family` (≈L109) anchors on a `p`-cycle (`_cycle_state`), reaches it
    (`_word_to`), separates phases (`_distinguish`); **leaves `u`/`x` None if no
    separator** — already correct behaviour, just not consumed.
  - `_distinguish` (≈L90) — `product(q, complement(q'))​.accepting_word()`; returns None
    when residuals coincide (spurious). **Only compares `q` to its adjacent phase
    `t[q]`** (called at ≈L123) — sound but not complete.
- `aut2ltl/witness/` — the `Witness` dataclass (`u`, `v`, `x_prefix`/`x_cycle`, `p`).

## The fix (the TODO)

1. Treat **completed witness** (both `u` and `x` present) as the authority for an
   absorbing `NOT_LTL` — even above SAT-min (extends the conclusive regime).
2. **No completed witness** on a non-aperiodic reading ⇒ **abstain**: a *non-absorbing*
   decline (never build — preserves the no-wrong-formula guarantee — but do not claim a
   proof and do not dominate the portfolio). NOT "let `inner` build" (that risks a wrong
   formula on a genuinely non-LTL language).
3. Before flipping behaviour: **widen `_distinguish`** to compare *all* phase pairs, not
   just `q`/`t[q]` — otherwise a real count surfacing only between non-adjacent phases is
   missed (sound but a false abstain → completeness loss). Then completion failure is a
   trustworthy "spurious" signal.
4. `extract_witness` must run (and be checked for completion) on the verdict path, not
   only knob-guarded for diagnosis. Decide the `produce_witness=off` fallback (probably:
   keep the current SAT-min behaviour as a labelled hint when witnesses are disabled).

## Verify first (don't flip blind)

- **Construct a star-free ω-language whose `det_generic_minimal()` is non-aperiodic with
  no completable witness** — a concrete spurious group / false negative. If found: the
  regression fixture, and proof the live tool is exposed. If it stubbornly resists across
  the corpus: say so explicitly (the generic+SAT-min form may be faithful enough in
  practice) rather than assume.
- Scan the corpus `not-LTL` verdicts (benchmark 64, kinska 63) for any whose witness does
  **not** complete — those are the suspects. (Survey does not equivalence-check NOT_LTL
  verdicts, so a false negative passes silently today.)

## Provenance

Crux raised reviewing `tester/algorithm.md` (the "faithful to the syntactic semigroup"
overclaim) and confirmed against `witness/algorithm.md` (the "distinguishability on the
minimal form guarantees `x` exists" overclaim — false for ω). Both sentences corrected
2026-06-30; the Soundness paragraph (tester) and the completion-failure semantics
(witness Scope) now state the one-way verdict. This note is the code-side follow-up.
