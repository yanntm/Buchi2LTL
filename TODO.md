# aut2ltl — Project TODO

Open project-level items only. Completed campaigns are recorded in `docs/HISTORY.md`
and git history. (The big docs + contract/combinator refactors + the `decomp/` regroup
and the `kr → bls` engine reorg all landed — see HISTORY 2026-06-17.)

## Corpora / test harness

- **`counting_buchi_1ap_07`: investigate the r3-simplify runtime degradation; try to
  bound it.** After moving to the stronger (r3-containment) `tl_simplifier`, this one
  kinska/counting input went from a 10 s build (DAG 47) to a **90 s** build (DAG 48) —
  it pays the full r3 cost for *no* size gain, unlike the rest of the counting family
  (whose DAGs roughly halved). Not a hang and not a validation failure: it completes,
  but blows the survey's per-example budget so the reference CSV records `TIMEOUT`.
  Profile which simplify/containment call spends the ~80 s and see if it can be bounded
  (time/effort cap on r3 containment) without losing the corpus-wide wins. Until then
  this is an **accepted new Pareto point** (size ↓ across the family, runtime ↑ on this
  one), and the reference runs reflect it.
- **Profile / instrument the `Memo` object and diagnose.** The shared-store
  `(operation, Language)` op-cache (`combinators/memo`, wired through `deep_nobls_memo`)
  *should* save massive numbers of calls — but the survey is perf-flat (`deep_nobls_memo`
  is output-identical to `deep_nobls` with build time within ±2% noise on all three
  corpora, see `logs/opcache2/`). So the cache is not doing its job: either it barely
  hits (few repeated `(op, language)` pairs at the granularity we wrap), or the cost the
  memo was meant to collapse lives outside the memoized path (the un-memoized `cakedsdet`
  seed internals, the final outer `Simplify`, or per-node work that does not recur).
  Instrument `Memo` with hit/miss/insert counters per operation (and total children
  computed vs cache size), run one telling input (kinska `counting_buchi_1ap_18`, the
  `gate_count.py` motivation) and confirm whether the hit rate matches the expected
  240×-style redundancy or is near zero. Fix the wiring (or conclude the redundancy
  isn't there) from the numbers.
  **Known wiring gap (prime suspect):** `deep_nobls_memo` depth-caches only the *arm*
  (`_nobls_memo` inlines `nobls` so each primitive is store-wrapped); the forward seed is
  `m(cakedsdet(options))` — the whole recipe wrapped in ONE `Memo`, so only its outermost
  call is cached, and `as_translator` calls the seed once per top language, so that entry
  is written once and never reused. None of cakedsdet's internal peel/decompose/bls work
  is on the shared store, and it cannot share with the arm's re-presentation of the same
  sub-languages (different, uncached instances). To make the memo actually save calls the
  seed must be inlined and depth-wrapped on the same store, like `nobls` (cakedsdet is a
  cake/bls engine, so its primitives differ from the arm's).
  **Candidate fix landed (2026-07-02, unmeasured): `recipes/deep_memo.py`** — the whole
  pipeline inlined on one store, and the seed's rich arm and the deep arm are ONE
  instance (rich ≡ nobls, so they now share entries). The instrumentation/measurement
  half of this item is still open: run `gate_count.py` / the counting inputs against
  `--use deep_memo` and read the hit rates.
- **Finer per-Spot-call control (decouple construction-translate from verify).**
  Surfaced by the `deep_nobls` @1000 genaut run (research_notes/roundtrip_log.md): the
  round trip's `ltl2tgba` calls are guarded only by a *flat-size* proxy
  (`language.translate_tree_limit`), never *time*-bounded per call. So one runaway Spot
  translate inside the round trip blows the whole-survey 15 s build budget and kills an
  answer that was nearly fully collapsed, instead of declining that *one* node (which
  `best_of([identity, …])` would absorb). Push a per-call **time + size** bound down into
  `language.translate` so an overboard call raises `UntranslatableLanguage` for that node
  only → graceful per-node degradation, not a global timeout. Separately, the construction
  translate budget and the verification (equiv-oracle) budget are distinct concerns and
  should stay independently controllable.
- **Convert the benchmark examples to HOA.** Split `samples/benchmark/inputs/`
  into `ltl/` + `hoa/` like `samples/{validation,fixtures}`, generating the HOA
  with `survey.ltl2hoa` (our inputs are not explosive for Spot). Lets the
  benchmark exercise the HOA entry path, not just LTL — preliminary to new-algo
  experiments. (Deferred from the survey/tests refactor — see HISTORY 2026-06-23.)

## Portfolio / combinators

- **Own-simplify rules for anchor-shaped output.** The anchored read-off
  (`aut2ltl/anchor`, wired in `recipes/deep_anchor.py`) emits machine-shaped
  patterns Spot's simplifier does not reduce; add targeted O(DAG) own rules.
  First confirmed candidate: `F(p ∧ X(p U q)) ≡ F(p ∧ X q)` (slide to the last
  `p` of the block — seen as `F(b & X(b U !a))` vs the default's `F(b & X!a)` on
  `collapse_example`). Collect more from the deep_memo/deep_anchor A/B diffs.

- **daisystar (non-deterministic case): close the flat `LEAVE`.** For a
  *non-deterministic* rejecting star the flat `daisystar` `LEAVE` reuses daisy2's
  move-level `stay` region and stays **gate-rescued** (same open form as daisy2
  Target B). (a) Find a closed `stay`, or prove it leaves LTL; (b) decide whether
  `daisy2`, `daisystar`, `daisystardet` should **fuse** into one star peel
  dispatching on the SCC tag + L-partition determinism. (The deterministic case is
  already exact via `daisystardet` — `aut2ltl/daisystardet/algorithm.md`.)
- **Benchmark `best_inv_loop` (inv per-descent).** The `recurse` brick now lets the
  invariant strip ride every descent level (`daisy_pair_inv`); A/B it vs
  `best_daisy2` on the full benchmark — total size, and especially whether
  per-descent `inv` makes NOT_LTL verdicts cheaper / decidable on the kinška
  `counting/` automata (where `best` currently times out, by shrinking the monoid
  the LTL-definability gate tests). Top-only `best_inv` is benchmark-neutral (the
  global `Σ = ⋁(all guards)` is usually vacuous); the per-descent local `Σ` is the
  one that should fire.
- **Memoize `recurse` subproblems on the `Language`** (free DAG sharing across a
  descent). The decomposition-unification half of the old `recurse(decompose, combine,
  floor)` idea landed (`aut2ltl/decomp/decompose.py`, all three decomposers); the open
  levers on the `recurse` seam are memoization and a per-descent `best_of`.
- **Retire the transitional shim** `aut2ltl/contract.py` once importers repoint.
- **`fuse2` is unwired** (`heur/fuse2`). Decision: leave it out; let fuzzing measure
  whether its absence costs `best` before deciding to wire it.
- **Improve `bls/operators/` tracing: only compute a trace string when it will be
  printed.** The `_trace(f"… {_short_f(…)} …")` call sites (solid/reach/fin/wsolid/
  dashed, via `support.py`) build the message — flattening formulas — *before* the
  `_TRACE` guard runs, so the cost is paid even when tracing is off. Convert them to
  inlined `if _TRACE:` guards (and honor the global `TRANSLATOR_TRACE_ON` knob), as
  done for the daisy* translators.

## Open

- **Non-LTL phase 3 — remaining fronts** (fixes 1–4 landed 2026-07-01/02: fail-safe
  gate with certified-or-decline + oracle fence; exhaustive linear completion; the
  ω-power witness shape; boundary revalidation at decompose + the daisy peels — see
  `docs/HISTORY.md` and root `witness3.md` for the full state):
  - **Seam refinements**: decompose revalidation via the parts algebra (membership
    per child + connective — no parent-sized product); daisy petal-drop exactness
    lift (restrict the lifted guard to `g ∧ ¬σ ∧ ⋀¬g_sib`, BDD-only, no replay).
  - **Parent completion seeded by the child's `v`** (no GAP on the whole): when the
    parts algebra fails at a decomposer, re-run linear/ω-power completion on the
    parent's det form with the child-provided group element — recovers certified
    rejections for evenblocks-class inputs (both children non-LTL, families masked
    by the intersection).
  - **Cascade self-fence**: decline on a group component inside the holonomy parse
    (today it is misread as a reset). Makes bls sound on ANY form by construction;
    the gate becomes an optimization; closes the generic-vs-sbacc form gap.
  - **Route B (completeness on spurious groups) — SUPERSEDED by the exact oracle**
    (`bls/definability/oracle/`, landed 2026-07-02): the syntactic-ω-semigroup
    quotient decides the abstain zone exactly (`gf_aa_parity` → definitive LTL, no
    SAT search needed). **Remaining: wire the oracle into the gate** — replace the
    `PROBABLY_NOT_LTL` decline branch with a `decide()` call (tester screen stays
    the fast path), pick the `em_cap` policy, then refresh the reference CSVs
    (declines become verdicts on both sides).
  - **Housekeeping**: rerun genaut `2state1ap1acc` clean (the 2026-07-01 background
    run mixed two code states); refresh the validation/kinska/benchmark references
    (NOT_LTL rows changed technique and some verdicts became declines); fold the
    durable conclusions of `witness3.md` into the algorithm docs.
- **(superseded — kept for context) Condition the hard NOT_LTL verdict on an
  actually-completed witness (soundness).**
  `bls/definability/gate.py` currently emits an absorbing, "proof"-labelled `NOT_LTL`
  keyed on `label_ltl_definable` (aperiodicity + SAT-min) alone; the witness is
  decorative (`gate.py:85`). But in the ω-setting `TM`-aperiodic ⟹ LTL is the only sound
  direction — a group in `TM` may be a determinisation artefact, so `not-aperiodic` is a
  *hint*, not a proof. The proof is a **completed** `(u,v,x)` family (minimality-
  independent). Fix: only the completed witness yields an absorbing `NOT_LTL`; no `x`
  found ⇒ abstain (non-absorbing decline, never build), not reject. Caveat to resolve
  first: `_distinguish` only compares adjacent phases (`witness.py:123`), so it is sound
  but not complete — widen to all phase pairs before flipping behaviour, and find a
  spurious-group example to use as the regression fixture. Full context + pointers:
  root `nonltl.md`. (Docs already corrected: `tester/algorithm.md` Soundness/
  Conclusiveness, `witness/algorithm.md` Scope.)
  **Witness lift landed (the "travels up the chain" half).** A peeler now lifts a
  NOT_LTL child's witness back across its peel: `LTLResult.prefix` prepends the consumed
  prefix to the anchor `u` (`Witness.prepend`) and stamps the peeler's own technique on
  the verdict. `daisy` and `daisy2` (the single stem guard) and `daisystardet` (a reaching
  word through the SCC, `shape.exit_word`) are done; the kinska `counting/2ap` cluster —
  the former FAIL target — now validates TRUE, and both grafted fixtures
  (`samples/validation/hoa/prefix_nonltl_{1,2}.hoa`) pass. **Remaining:** no other peeler
  has been observed emitting a NOT_LTL witness; any that does gets the same lift. Still open
  here is the *other* failure mode — an incomplete / spurious-group witness (no `x`) ⇒
  **abstain**, not FAIL — which is the `_distinguish` widening + completed-witness gating
  described above.
- **Output size at scale (the live research front).** The construction is cheap; the
  flat form explodes and Spot hits its 32-acceptance-set wall. Representation/
  verification, not fidelity. Analysis: `docs/dag_folding.md`.
- **Flags manual.** The `--use` / `-O` reference doc the root README points to (add
  the `--use best` recipe and the recipe-vs-leaf distinction).
- **README: stdout/output contract moved — refresh once stabilized.** stdout is now
  kind-tagged (`LTL: <formula>` / `NOT_LTL: <witness>`), no longer a bare-formula
  filter, so the `-q | ltlfilt` examples are stale (ltlfilt is a no-op on our massaged
  output anyway). A bare/pipe mode may be retrofitted later. Also document the NOT_LTL
  witness line + the `aut2ltl.verifier` package, and the survey CSV's new `check_s`
  column (verify wall-time). Hold until the IO settles.

## Deferred (intentional — revisit only if needed)

- **Options wiring, Buckets 2 & 3.** The remaining `KR_*` knobs (fuse_letters,
  fold_fin_reach, simp.*, tracing, resource/safety limits) are declared in the package
  `options.py` contracts but still read from `os.environ`. Process-scoped by nature,
  so they stay env unless per-instance A/B is ever required.
- **Infra compartment.** Share `bdd_dict`/buddy and the DAG unifier as refs on the
  threaded context (the Options and Caches compartments already landed).
