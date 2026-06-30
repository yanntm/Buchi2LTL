# The LTL-definability decision

`label_ltl_definable(L)` decides whether the ω-language of a `Language` is
LTL-definable and caches the verdict on the Language. It is not itself a Translator
(it emits no formula); it is the gate the kr cascade — a Translator — runs before it
builds. The cascade is unsound on a non-definable language: the holonomy
decomposition still succeeds, but emits a group component the parser reads as a
reset, yielding a wrong formula. The language is filtered first.

## The input

Like every Translator, the gate asks the `Language` for one representation and works
on that alone. It asks for `Language.det_generic_minimal()`: the language
determinized to a deterministic generic-acceptance automaton
(`postprocess(deterministic, generic)`), then state-minimized with Spot's
`sat_minimize` when the automaton is small enough — best-effort, falling back to the
unminimized deterministic form otherwise. The gate then completes it before
extraction; completion only adds a sink — an idempotent — so it cannot perturb
aperiodicity.

The form is read so its transition monoid can be tested for aperiodicity. What that
test does and does **not** prove about the *language* — the crux in the ω-setting — is
the subject of **Soundness** below. Minimization is best-effort and only attempted
below a size threshold, which the **Conclusiveness** rule keys on.

## The characterization it tests

```
LTL  =  FO[<]  =  star-free  =  counter-free  =  transition monoid aperiodic
```

These equalities are McNaughton–Papert / Schützenberger for finite words. They carry
over to ω-words (Thomas; Perrin–Pin), with the **syntactic ω-semigroup** as the object
required to be aperiodic and the transition-monoid test serving as the computable proxy
— sound in one direction only (see Soundness).

**Aperiodic = group-free**: no element `g` has a non-trivial cyclic orbit
`g, g², …, gᵖ = 1` with `p > 1`. A non-trivial group in the monoid is exactly the
ability to count modulo `p`, which counter-free LTL cannot express. The decision
reduces to one question on the monoid of the input automaton: is it aperiodic? The
oracle is `gap/aperiodic.is_aperiodic_gens` (build the semigroup from the generator
images, call GAP's `IsAperiodicSemigroup` — the cheap boolean, no holonomy). This
package owns the policy around that call; the GAP script stays in `gap/`, the
Spot→generators extraction in `extract.py` (both shared with the cascade's holonomy).

## Soundness (what the algebraic verdict proves)

The check reads the transition monoid `TM` — the transformations the letters induce on
states — which depends only on the transition function, not the acceptance.

*Finite words.* The states of a minimal DFA are exactly the right-congruence
(Myhill–Nerode) classes `u⁻¹L`, and the minimal DFA's transition monoid is isomorphic to
the syntactic monoid; aperiodicity is then a Schützenberger invariant of the language,
independent of any encoding.

*ω-words (our case).* This does not transfer cleanly. For any deterministic automaton
recognizing `L`, words acting identically on all states are interchangeable in every
context, so the syntactic ω-semigroup `S` is a **quotient** of `TM`. Aperiodicity passes
through a quotient in one direction only, so the verdict is **one-way**:

- **`TM` aperiodic ⟹ `L` is LTL.** `S`, a quotient of an aperiodic monoid, is aperiodic,
  hence `L` is star-free = FO[<] = LTL. A proof, independent of the acceptance and of
  state-minimality.
- **`TM` not aperiodic ⇏ `L` is not LTL.** The group may live only in `TM` and collapse
  in the quotient `S` — an artefact of the deterministic encoding. Unlike a minimal DFA,
  a state-minimal ω-automaton can keep two states with *equal* residual ω-languages apart
  because the acceptance condition needs the memory; a group permuting such states is
  determinisation noise, not language counting. The generic form and SAT-minimization
  remove *some* such artefacts (the sbacc counter below, redundant-state groups) but are
  **not** known to remove all; we do not claim `TM` is faithful to `S`.

So the gate is a sound **acceptor** of LTL and only a **filter** for non-LTL. A
`not-aperiodic` reading is a *candidate* non-definability, promoted to a proof only by
the sibling `witness/` package, which extracts the counting family `(u, v, x, p)` from
the offending group and verifies it separates words **in `L`** itself. Absent that
confirmation it is a hint, not a proof (see Conclusiveness).

## Why generic acceptance, not the cascade's state-based form (`sbacc`)

The cascade builds from `det_parity_sbacc()`, which the gate must not reuse. Forcing
state-based acceptance degeneralizes a generalized-Büchi condition (e.g.
`Inf(0)&Inf(1)&Inf(2)` for `GFa & GFb & GFc`) by adding a round-robin "which mark am I
waiting for" index. That index is a cyclic group in the transition monoid — an artefact
of the acceptance encoding, not of the language — so it reads as non-aperiodic even when
the language is LTL. The generic-acceptance form carries no such counter; it removes
*this* encoding artefact (though, per Soundness, not every determinisation artefact).

## Conclusiveness (the SAT-min rule)

`det_generic_minimal()` SAT-minimizes `D` only at or below a threshold
(`SAT_MIN_STATES`); above it the form may be non-minimal, and a group can act on
redundant equivalent states the language does not see. SAT-minimization removes *that*
family of spurious groups — but, per **Soundness**, it does not by itself make a
`not-aperiodic` reading a proof of non-definability: the ω quotient gap (equal-residual
states the acceptance keeps apart) survives minimization. The authoritative proof of
rejection is a **completed witness**, not the algebraic reading. The decision returns a
pair:

```
label_ltl_definable(L)  →  (definable, conclusive)
```

- `definable` — the sbacc-free transition monoid is aperiodic. When true this *is* a
  proof (`TM` aperiodic ⟹ LTL); the gate delegates to the cascade.
- `conclusive` — `n_min ≤ threshold`: the cheap algebraic confidence that a group, if
  present, is not merely a redundant-state artefact. It is *not* a standalone proof of
  non-definability — that is the witness's job (`witness/algorithm.md`).

The consumer (`gate.py`) currently emits the non-definable reading as a `NOT_LTL`
`LTLResult` keyed on `conclusive`, with the witness attached as a diagnosis complement.
Conditioning the hard, absorbing `NOT_LTL` on an actually-*completed* witness (no `x` ⇒
abstain, not reject) is a pending soundness item — see the root `TODO.md`.

## The verdict is absorbing

`NOT_LTL` is not a recoverable decline: it dominates both result algebras
(`aut2ltl/result.py`), so it governs the whole portfolio, not only the cascade.

- Choice (`first_success`): `NOT_LTL ≻ DECLINED`. A `DECLINED` falls through to the
  next translator, but a `NOT_LTL` short-circuits — `first` returns it as-is and no
  later member runs.
- Composition (`credit`/`fuse`): `NOT_LTL ≻ DECLINED ≻ OK`. A `NOT_LTL` child raises
  its parent to `NOT_LTL` and clears the formula.

Hence one member's non-definability verdict is final: no downstream translator can
override it.

## When the oracle cannot run (the gate abstains)

The gate is permissive in one case, and it is not the verdict: when the oracle
cannot run at all — too many APs to extract a tractable letter set, or a GAP
error/timeout. It then **abstains**, returning `(definable=True, conclusive=False)`: it
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

The verdict is computed once per Language and tagged via `set_ltl_definable`; a
cached `(definable, conclusive)` short-circuits the call. The gate is the single
choke point for all cascade members — each runs only after it — so one GAP call
serves the whole portfolio pass over a Language.

## Modules

- `tester.py` — `label_ltl_definable`: pull `det_generic_minimal()`, gate
  `conclusive` on the SAT-min threshold, complete and extract generators, run the
  aperiodicity oracle, abstain on error, cache the pair.

## Layering

Sits above the floor (reads `Language`, `SAT_MIN_STATES`) and above the GAP oracle
(`gap/aperiodic`) and the extractor (`extract`). It imports neither `Cascade` nor any
`Translator`, so it composes into the cascade gate without a cycle. Consumer:
`aut2cas.py`, just before the holonomy build.

> Forward note: on the non-definable branch the same transition-monoid group that
> fails aperiodicity is the carrier of a witness that demonstrates non-LTL-ness (a
> counting family `(u, v, x, p)`). Extracting and checking it is a separate
> concern, owned by the sibling `witness/` package; see `witness/algorithm.md`.
