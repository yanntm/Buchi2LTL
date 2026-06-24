# The LTL-definability decision

`label_ltl_definable(L)` decides whether the ω-language of a `Language` is
**LTL-definable**, and caches the verdict on the Language. It is not a Translator
(it emits no formula) — it is the **gate** the kr cascade consults before it
builds, because the cascade is *unsound* on a non-definable language: the holonomy
decomposition still succeeds, but it emits a **group** component the parser treats
as a reset, from which a *wrong* formula is built. So the language must be filtered
first.

## The characterization it tests

```
LTL  =  FO[<]  =  star-free  =  counter-free  =  the deterministic
                                                 transition monoid is APERIODIC
```

Aperiodic = **group-free**: no element `g` has a non-trivial cyclic orbit
`g, g², …, gᵖ = 1` with `p > 1`. A non-trivial group inside the monoid is exactly
the ability to **count modulo `p`**, which counter-free LTL cannot express. So the
whole decision reduces to one algebraic question about the transition monoid of the
deterministic automaton: *is it aperiodic?*

The oracle that answers it is `gap/aperiodic.is_aperiodic_gens` (build the
semigroup from generator images, call GAP's `IsAperiodicSemigroup` — the cheap
boolean, **no** holonomy). This package owns the *policy* around that call; the GAP
script stays in `gap/`, the Spot→generators extraction stays in `extract.py` (both
shared with the cascade's holonomy bridge).

## The form the oracle must run on (the sbacc trap)

The verdict must be read on a **`sbacc`-free, generic-acceptance, minimized**
deterministic form — `Language.det_generic_minimal()` — and **not** on the
cascade's own automaton.

The cascade is built from `det_parity_sbacc()`, whose *forced* state-based
acceptance **degeneralizes** a generalized-Büchi condition (e.g.
`Inf(0)&Inf(1)&Inf(2)` for `GFa & GFb & GFc`) into a "which mark am I waiting for"
counter. That counter is a **spurious cyclic group**: it reads as non-aperiodic on
a language that *is* LTL. Running the oracle on the sbacc form would therefore
reject definable languages. `det_generic_minimal()` carries the acceptance
generically, with no such counter, so its transition monoid reflects the language
and not the encoding.

Completion before extraction is safe: `extract_generators` needs a complete
deterministic automaton, and completing only adds a **sink** — an idempotent, no
group — so it cannot perturb the aperiodicity verdict.

## Conclusiveness (the SAT-min rule)

A `not-aperiodic` reading is a **proof of non-definability only on a genuinely
state-minimal form**. `det_generic_minimal()` SAT-minimizes `D` only at or below a
threshold (`SAT_MIN_STATES`); above it, the form may be non-minimal, and a group
can act on **redundant equivalent states** — structure the language does not
actually see. So the decision returns a pair:

```
label_ltl_definable(L)  →  (definable, conclusive)
```

- `definable` — the sbacc-free transition monoid is aperiodic.
- `conclusive` — the verdict was read at/below the SAT-min threshold, so a
  `not definable` reading is a **proof**; above it, it is only a **strong hint**
  (the automaton may be non-minimal). `conclusive` is `n_min ≤ threshold`.

The consumer (`aut2cas.py`) emits the non-definable reading as a `NOT_LTL`
`LTLResult` **before** the holonomy build is ever called — a flat NOT_LTL when
conclusive, a hedged "strong hint, may be non-minimal" otherwise.

## The verdict is absorbing

`NOT_LTL` is not a recoverable decline: it dominates both result algebras
(`aut2ltl/result.py`), so it governs the whole portfolio, not only the cascade.

- **Choice (`first_success`).** `NOT_LTL ≻ DECLINED`: a `DECLINED` falls through to
  the next translator, but a `NOT_LTL` short-circuits — `first` returns it as-is and
  no later member runs.
- **Composition (`credit`/`fuse`).** `NOT_LTL ≻ DECLINED ≻ OK`: a `NOT_LTL` child
  raises its parent to `NOT_LTL` and clears the formula.

Hence one member's non-definability verdict is final: no downstream translator can
override it.

## When the oracle cannot run (the gate abstains)

The gate is permissive in one case, and it is not the verdict: when the oracle
cannot run at all — too many APs to extract a tractable letter set, or a GAP
error/timeout. It then abstains, returning `(definable=True, conclusive=False)`: it
neither emits `NOT_LTL` (which would reject a possibly definable language over an
extraction limit) nor asserts definability as fact, so the cascade is attempted
rather than the language rejected unseen. The asymmetry favours completeness: an
abstention costs at most a later cascade decline, whereas a spurious rejection would
discard a definable answer.

Abstaining preserves soundness. The gate and the cascade share the same machinery
(`extract_generators` and GAP); a failure that blocks the cheap aperiodicity check
also blocks the cascade's holonomy, which runs the same extraction and a larger GAP
job. On such inputs the cascade therefore declines rather than building a formula,
so the tool never returns a non-equivalent formula.

## Caching

The verdict is computed **once per Language** and tagged via `set_ltl_definable`;
a cached `(definable, conclusive)` short-circuits the call. The gate is the single
choke point for *all* cascade members — each runs only after it — so one GAP call
serves the whole portfolio pass over a Language.

## Modules

- **`tester.py`** — `label_ltl_definable`: pull `det_generic_minimal()`, gate
  `conclusive` on the SAT-min threshold, complete + extract generators, run the
  aperiodicity oracle, abstain on error, cache the pair.

## Layering

Sits **above the floor** (reads `Language`, `SAT_MIN_STATES`) and **above the GAP
oracle** (`gap/aperiodic`) and the extractor (`extract`). It imports **neither**
`Cascade` nor any `Translator`, so it composes into the cascade gate without a
cycle. Consumer: `aut2cas.py`, just before the holonomy build.

> Forward note: on the *non-definable* branch the same transition-monoid group that
> fails aperiodicity is the carrier of a **witness** that demonstrates non-LTL-ness
> (a counting family `(u, v, x, p)`). Extracting and checking it is a separate,
> not-yet-built concern; see `research_notes/non_ltl_certificates.md`.
