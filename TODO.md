# aut2ltl — Project TODO

Open project-level items only. Completed campaigns are recorded in `docs/HISTORY.md`
and git history. (The big docs + contract/combinator refactors + the `decomp/` regroup
and the `kr → bls` engine reorg all landed — see HISTORY 2026-06-17.)

## Corpora / test harness

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

## Open

- **Output size at scale (the live research front).** The construction is cheap; the
  flat form explodes and Spot hits its 32-acceptance-set wall. Representation/
  verification, not fidelity. Analysis: `docs/dag_folding.md`.
- **Flags manual.** The `--use` / `-O` reference doc the root README points to (add
  the `--use best` recipe and the recipe-vs-leaf distinction).

## Deferred (intentional — revisit only if needed)

- **Options wiring, Buckets 2 & 3.** The remaining `KR_*` knobs (fuse_letters,
  fold_fin_reach, simp.*, tracing, resource/safety limits) are declared in the package
  `options.py` contracts but still read from `os.environ`. Process-scoped by nature,
  so they stay env unless per-instance A/B is ever required.
- **Infra compartment.** Share `bdd_dict`/buddy and the DAG unifier as refs on the
  threaded context (the Options and Caches compartments already landed).
