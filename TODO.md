# aut2ltl — Project TODO

Open project-level items only. Engine work items live in `aut2ltl/kr/TODO.md`;
the record of completed campaigns is in git history and `docs/HISTORY.md`.

## Open

- **Wire `PartScc` into the portfolio / CLI.** The `aut2ltl.partscc` leaf
  (`PartScc()`, a `Translator`) is built, tested, and gate-clean but not reachable
  from `-m aut2ltl`. It reconstructs a `Language` whose state-based automaton is a
  single terminal SCC (the "stay in this SCC forever" sub-language) — exactly what
  the sl engine hands an exit target via `of(A↓dst)`. Wire it as a leaf in the
  sl-driven delegate chain in `aut2ltl/portfolio/` (sl peels marguerites and
  delegates the rerooted suffix; partscc labels it; the crossing `X` is sl's
  ordinary exit rule — no entry-timing cooperation needed). `Language.of` now
  cleans rerooted sub-languages (purged states, dropped orphan APs), so clean
  single-SCC inputs materialize. Then validate against the t2 fixtures
  (`tests/fixtures/t2_successes.py`, `terminal_2scc_labeled.py`) and the survey's
  partscc stress block to measure coverage vs the legacy t2. End goal: retire
  `aut2ltl/sl/heuristics/terminal_2scc.py` and its sl entry-timing surgery
  (`scc_entry_I` / `direct_scc_sync_attach` in `sl/reconstruction.py`), which the
  pure-leaf framing makes unnecessary.

- **Output size at scale (the live research front).** The construction is cheap;
  the cost is the flat form — Spot hits its 32-acceptance-set tableau limit and
  the largest flat strings explode. This is representation/verification, not
  fidelity. Analysis and candidate counter-measures: `docs/dag_folding.md`.

- **`best_of` combinator.** The portfolio optimizes for the FIRST success, not the
  smallest output — but size is the research objective. Add `best_of([...],
  key=cost)` beside `first_success`, plus a `cost`/size field on
  `LTLResult` (the dataclass is pre-shaped for it). Until then, cited order
  is the only size heuristic.

- **HOA input to the survey.** `tests/survey.py` currently feeds LTL strings only;
  the tool already accepts HOA files. Extend the survey (and corpus) to take HOA
  inputs, with the equiv oracle comparing against the source automaton.

- **Docs rewrite (in progress).** Top-level README/STATUS/TODO + CLAUDE done; the
  `aut2ltl/kr` README/STATUS/TODO trio still carries campaign history that belongs
  in `docs/HISTORY.md`.

## Deferred (intentional — revisit only if needed)

- **Options wiring, Buckets 2 & 3.** The remaining `KR_*` knobs (fuse_letters,
  fold_fin_reach, simp.*, tracing, resource/safety limits) are declared in the
  package `options.py` contracts but still read from `os.environ`. They are
  process-scoped by nature (sound always-on optimizations, or global limits/
  tracing), so they stay env unless per-instance A/B is ever required.

- **Infra compartment.** Share `bdd_dict`/buddy and the DAG unifier as refs on the
  threaded context (the Options and Caches compartments already landed).
