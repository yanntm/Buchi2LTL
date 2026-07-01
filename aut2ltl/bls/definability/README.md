# aut2ltl.bls.definability — the LTL-definability gate

The kr cascade is **unsound on a non-LTL language**: the holonomy decomposition
still succeeds, but emits a group component the parser reads as a reset,
yielding a wrong formula. So a non-definable `Language` must be intercepted
*before* the cascade builds. This package owns that border. The question it
decides is algebraic —

```
LTL  =  star-free  =  syntactic ω-semigroup aperiodic
```

— but the computable reading (aperiodicity of a deterministic form's transition
monoid) is **one-sided**: aperiodic is a proof of LTL, a group is only a
suspicion (see `tester/algorithm.md`, Soundness). The gate therefore has three
outcomes, not two:

| tester reading | witness outcome | gate result |
|---|---|---|
| aperiodic | — | delegate to `inner` (the cascade builds) |
| group | family completed **and** certified by replay | **`NOT_LTL`**, absorbing — a proof |
| group | no certified family | **`PROBABLY_NOT_LTL`**, non-absorbing — `inner` is never called, other translators stay free to answer |

The fail-safe invariant: an absorbing rejection is issued **only** on a
certified counting family; an uncertified suspicion never rejects and never
builds. A wrong absorbing `NOT_LTL` is thereby impossible, and the cost of a
spurious group is bounded by the loss of the cascade on that one input — every
other translator is individually sound (faithful-or-decline), so nothing else
needs the fence.

It builds no LTL itself; it gates the translator that does.

## Modules

- **`gate.py`** — `definability_gate(inner)`: the border, as a Translator
  decorator. On each `Language` it asks the tester for the algebraic reading;
  on a suspicion it asks the witness for a certified family, replaying it
  in-process (bounded) before absorbing. It is the single owner of "why not
  LTL": the prose diagnosis, the technique tag, and the witness on the result.

- **`tester/`** — `label_ltl_definable`: the algebraic reading. Pulls
  `det_generic_minimal()` (the sbacc-free form), runs the aperiodicity oracle on
  its transition monoid, tags the Language `(definable, conclusive)` so one GAP
  call serves the whole portfolio pass. See `tester/algorithm.md` for the
  one-sided soundness argument, the sbacc trap, and the abstain rules.

- **`witness/`** — `extract_witness`: on the suspect branch, extracts and
  completes a counting family — linear `u·vⁿ·x` or ω-power `u·(vⁿ·y)^ω` — the
  certificate that, once replayed, proves non-LTL-ness. See
  `witness/algorithm.md` for the two shapes, their soundness and joint
  completeness, the exhaustive completion, and the lift rules across peels.

## Layering

```
gate ──► tester   (label_ltl_definable: definable, conclusive)
     ──► witness  (extract_witness: the Witness material, both shapes)
     ──► replay   (aut2ltl/verifier: in-process membership check, bounded)
     ──► floor    (LTLResult, Translator, Witness)
```

The package sits above the floor (`Language`, `SAT_MIN_STATES`), the GAP oracle
(`gap/`), the extractor (`extract`), and the engine-agnostic verifier. It
imports neither `Cascade` nor any `Translator`, so it composes around the
cascade adapter without a cycle. `from aut2ltl.bls.definability import
label_ltl_definable, definability_gate` is the public surface.
