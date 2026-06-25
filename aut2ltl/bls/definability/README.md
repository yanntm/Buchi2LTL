# aut2ltl.bls.definability — the LTL-definability gate

The kr cascade is **unsound on a non-LTL language**: the holonomy decomposition
still succeeds, but emits a group component the parser reads as a reset, yielding a
wrong formula. So a non-definable `Language` must be intercepted and reported as
`NOT_LTL` *before* the cascade builds. This package owns that border. The one
question it decides is algebraic:

```
LTL  =  star-free  =  counter-free  =  transition monoid aperiodic
```

It builds no LTL itself; it gates the translator that does.

## Modules

- **`gate.py`** — `definability_gate(inner)`: the border, as a Translator
  decorator. On each `Language` it asks the tester for the verdict and either
  builds the `NOT_LTL` `LTLResult` itself (the prose diagnosis plus, knob-guarded,
  the witness) and short-circuits, or delegates to `inner` (the cascade builds).
  It is the single owner of "why not LTL" and orchestrates its two peer leaves so
  neither depends on the other.

- **`tester/`** — `label_ltl_definable`: the raw verdict oracle. Pulls
  `det_generic_minimal()` (the sbacc-free form), runs the aperiodicity oracle on
  its transition monoid, and tags the Language with `(definable, conclusive)` so
  one GAP call serves the whole portfolio pass. See `tester/algorithm.md` for the
  algebra — the sbacc trap, the conclusiveness/SAT-min rule, the absorbing verdict,
  and the abstain rule.

- **`witness/`** — `extract_witness`: on the non-aperiodic branch, extracts the
  counting family `(u, v, x, p)` that certifies non-LTL-ness, carried alongside the
  `NOT_LTL` as a diagnosis complement. Same input and oracle machinery as the
  tester. See `witness/algorithm.md`.

## Layering

```
gate ──► tester  (label_ltl_definable: definable, conclusive)
     ──► witness (extract_witness: the Witness object)
     ──► floor   (LTLResult, Translator)
```

The package sits above the floor (reads `Language`, `SAT_MIN_STATES`) and above the
GAP oracle (`gap/aperiodic`) and the extractor (`extract`) — both shared with the
cascade's holonomy. It imports neither `Cascade` nor any `Translator`, so it
composes into the cascade gate without a cycle. Consumer: `aut2cas.py`, just before
the holonomy build. `from aut2ltl.bls.definability import label_ltl_definable,
definability_gate` is the public surface.
