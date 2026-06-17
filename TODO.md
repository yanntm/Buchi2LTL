# aut2ltl — Project TODO

Open project-level items only. Completed campaigns are recorded in `docs/HISTORY.md`
and git history. (The big docs + contract/combinator refactors + the `decomp/` regroup
and the `kr → bls` engine reorg all landed — see HISTORY 2026-06-17.)

## Portfolio rework (NEXT PRIORITY)

The component layer is complete: every engine/approach is a `Translator` (or
`CascadeTranslator`), composed by the floor combinator `first_success`. A scan of
`portfolio/` shows almost nothing intrinsically belongs there — the three composites
each map onto pieces that already exist or belong with their engine. Goal: portfolio
becomes a **thin, cunning assembly** offering convenience builders with reasonable
sub-assemblies pre-wired.

- **Retire `portfolio/decompose.py`.** `Decompose` is the old monolith of the
  AND-by-acceptance / OR-by-strength split — already extracted as `decomp/acceptance`
  + `decomp/strength` (+ `decomp/scc`). Compose those via `first_success` instead.
- **Move the sl adapter into `aut2ltl/sl/`.** `portfolio/sl.py` (`Sl`) is the sl
  engine's Translator façade; it belongs in the engine (like `daisy`/`decomp` expose
  theirs). Its flags (`portfolio/options.py`: `SL_ENABLED` / `SL_MAX_STATES` /
  `SL_VERIFY`) move with it.
- **Replace `SlDriven` with `Daisy(child=…)`** — `SlDriven` is the peel-and-delegate
  pattern over the legacy engine; `daisy` is exactly that, pure. Wire `Daisy` with a
  delegate; relocate `SlDriven` to `sl/` only if the legacy engine is still needed.
- **Slim `build.py`** to: the default assembly recipe (`first_success` / `best_of`
  over `{daisy, decomp/*, cascade, partscc, inv}`) + the `--use` name→translator
  table; settle the vocabulary (`str`/`bls` → `bls`/`muller`); offer convenience
  builders (pre-wired sub-assemblies).
- **`best_of` combinator + a `cost`/size field on `LTLResult`.** The portfolio picks
  the FIRST success; size is the research objective, so add `best_of([...], key=cost)`
  beside `first_success` (`LTLResult` is pre-shaped for a cost field).
- **Retire the transitional shims** once importers repoint: `aut2ltl/contract.py` and
  `aut2ltl/bls/bls.py`.

## Open

- **Wire `PartScc` into the assembly (part of the rework).** The `aut2ltl.partscc`
  leaf is built, tested, gate-clean, but not reachable from `-m aut2ltl`. It labels a
  single terminal SCC — exactly what a peel hands an exit target via `of(A↓dst)`. Wire
  it as a leaf alongside the cascade; validate against the t2 fixtures
  (`tests/fixtures/t2_successes.py`, `terminal_2scc_labeled.py`) and the survey's
  partscc stress block. End goal: retire `aut2ltl/sl/heuristics/terminal_2scc.py` and
  its sl entry-timing surgery (`scc_entry_I` / `direct_scc_sync_attach`).
- **Output size at scale (the live research front).** The construction is cheap; the
  flat form explodes and Spot hits its 32-acceptance-set wall. Representation/
  verification, not fidelity. Analysis: `docs/dag_folding.md`.
- **HOA input to the survey.** `tests/survey.py` feeds LTL strings only; the tool
  accepts HOA files. Extend the survey (and corpus) to HOA inputs, the equiv oracle
  comparing against the source automaton.
- **`Simplify` Translator decorator (tentative).** A decorator that simplifies a
  child's LTL output (own DAG rules and/or Spot) instead of each method simplifying;
  also eases debug traces. Evaluate; likely offer as a wrapping Translator.
- **Flags manual.** The `--use` / `-O` reference doc the root README points to.

## Housekeeping

- Two stale bls probes (`tests/kr/test_kr_zoom.py`, `tests/kr/measure_formula_dag.py`)
  import the removed `reachability` shell — repoint to `aut2ltl.bls.operators` or drop.

## Deferred (intentional — revisit only if needed)

- **Options wiring, Buckets 2 & 3.** The remaining `KR_*` knobs (fuse_letters,
  fold_fin_reach, simp.*, tracing, resource/safety limits) are declared in the package
  `options.py` contracts but still read from `os.environ`. Process-scoped by nature,
  so they stay env unless per-instance A/B is ever required.
- **Infra compartment.** Share `bdd_dict`/buddy and the DAG unifier as refs on the
  threaded context (the Options and Caches compartments already landed).
