# aut2ltl — Project TODO

Open project-level items only. Completed campaigns are recorded in `docs/HISTORY.md`
and git history. (The big docs + contract/combinator refactors + the `decomp/` regroup
and the `kr → bls` engine reorg all landed — see HISTORY 2026-06-17.)

## Portfolio / combinators

- **Benchmark `best_inv_loop` (inv per-descent).** The `recurse` brick now lets the
  invariant strip ride every descent level (`daisy_pair_inv`); A/B it vs
  `best_daisy2` on the full benchmark — total size, and especially whether
  per-descent `inv` makes NOT_LTL verdicts cheaper / decidable on the kinška
  `counting/` automata (where `best` currently times out, by shrinking the monoid
  the LTL-definability gate tests). Top-only `best_inv` is benchmark-neutral (the
  global `Σ = ⋁(all guards)` is usually vacuous); the per-descent local `Σ` is the
  one that should fire.
- **Refine `best_of`'s cost policy, then wire it in.** The brick landed
  (`aut2ltl/best_of/` + `LTLResult.cost`), still unwired. Open: (a) a **switch
  margin** so it keeps the first-cited form unless a challenger is smaller by a real
  margin — `dag_node_count` is noisy at the margin (a better-factored form can carry
  more nodes), so harvest the big collapses and ignore churn; the scalar stays
  swappable (e.g. temporals-first). (b) Swap a `first_success` for `best_of` where
  running every branch pays (the `recurse` seam; pairing an inv-variant with its
  non-inv form to keep only per-input wins).
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
- **Benchmark sub-project (`tests/benchmark/`).** A size bench, `default` vs `best`,
  reusing the survey engine over file-based `inputs/` (the survey corpus + W/U/R chains
  + 105 Kinská HOA; survey already routes HOA, oracle vs the source automaton — the old
  "HOA input to the survey" item, now done). Collection done for those three categories.
  Next: more categories, a *very* progressive `randltl` ladder (the construction is
  multiply-exponential — lean on the per-input timeout), and curation (dedup via
  `normalize.py`, a representative classified set). Reference: `tests/benchmark/logs/reference/`.
- **Flags manual.** The `--use` / `-O` reference doc the root README points to (add
  the `--use best` recipe and the recipe-vs-leaf distinction).

## Housekeeping

- Two stale bls probes (`tests/bls/test_kr_zoom.py`, `tests/bls/measure_formula_dag.py`)
  import the removed `reachability` shell — repoint to `aut2ltl.bls.operators` or drop.

## Deferred (intentional — revisit only if needed)

- **Options wiring, Buckets 2 & 3.** The remaining `KR_*` knobs (fuse_letters,
  fold_fin_reach, simp.*, tracing, resource/safety limits) are declared in the package
  `options.py` contracts but still read from `os.environ`. Process-scoped by nature,
  so they stay env unless per-instance A/B is ever required.
- **Infra compartment.** Share `bdd_dict`/buddy and the DAG unifier as refs on the
  threaded context (the Options and Caches compartments already landed).
