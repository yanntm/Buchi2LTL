# aut2ltl — Working Notes for Claude

## Project layout (nested root package `aut2ltl/`)
Layering, acyclic: `aut2ltl/contract.py` (LTLResult/Translator floor) +
`aut2ltl/language.py` ← `aut2ltl/bls` (pure cascade FoSSaCS engine) +
`aut2ltl/daisy` (pure self-loop peel) + `aut2ltl/partscc` (single-terminal-SCC
leaf) + `aut2ltl/heur` (extracted heuristics, e.g. `fuse2`) + `aut2ltl/decomp`
((de)composition approaches, one isolated subpackage each: `scc` / `strength` /
`acceptance` / `inv`) ← `aut2ltl/portfolio` (combinators: build / builder recipes)
← `aut2ltl/__main__` + `__init__`. Engine-agnostic helpers in `aut2ltl/ltl`
(metrics, printers, simplify). Tests under `tests/` (`survey*`, `tests/bls`,
`tests/heur`, `tests/fixtures`).

## Orientation (don't duplicate here — follow the pointers)
- `README.md` — repo guide / quick start. `STATUS.md` / `TODO.md` — project
  snapshot / open items.
- `aut2ltl/bls/README.md` — kr engine entry point: doc map, pipeline, module map,
  testing tools. `aut2ltl/bls/STATUS.md` — **current** engine state (read to start).
  `aut2ltl/bls/TODO.md` — engine work items.
- `docs/HISTORY.md` — construction log (the dated DONE/WIRED/LANDED/reverted
  record). Reference for the *why/when*; **do NOT read it to start a session** —
  STATUS.md is the current snapshot.
- `docs/algorithm.md` — the construction's scope/policy and module mapping.
  `docs/dag_folding.md` — the size-explosion analysis (open research direction).
- `paper/automata-to-ltl-construction.md` — the construction reference.
- `paper/Automata2LTL.txt` — ground truth for any formula-fidelity question
  (Sec 4.2 + Table 1 + Formulas 3/4/5 ≈ lines 440–1040). LLM summaries have twice
  introduced guard/case errors; the paper text settles disputes.
- The default translator is whichever recipe `RECIPES["default"]` points at in
  `aut2ltl/portfolio/recipes/` (do not hardcode its name elsewhere — the registry
  decides); `aut2ltl/portfolio/README.md` maps the package. The kr core stays pure.

## Discipline (mandatory)
- One commit per file (preference). The exception is a mechanical bulk change —
  code moved/renamed, a regex sweep, a baseline-log regeneration — which commits
  together. Otherwise commit freely without fretting over intermediate states
  (we are solo on `master`, so intermediate states are private). The commit
  message explains *the change*.
- **Committing** needs the user's go-ahead, then walk the files. **Pushing** is
  separate and ALWAYS asked for every time (no auto-approve): push only once the
  work is stable and the gates below have passed.
- Remember that git operations like `git mv` or `git rm` already populate the
  index. So always follow them with a commit *before* attempting to add any
  modified file to index.
- Commit directly to `master` (we do not branch). Never run branch / cross-branch
  diagnostics.
- `docs/HISTORY.md` is APPEND-ONLY via shell (`cat >>` / `printf >>`) and is
  NEVER read (it is large — STATUS.md is the snapshot). Record the *why/when* of a
  landed change there.
- NO persistent "memory" files: the user does not use them (not inspectable in the
  repo, they bloat unseen). Capture anything durable in STATUS / TODO / a README /
  this file instead — all git-inspectable.
- Update STATUS/TODO *before* committing a code change *when the change is a
  STATUS-level state shift or closes a TODO item*; a one-off bug fix that is
  neither belongs only in `docs/HISTORY.md`.
- Test BEFORE commit, via placed scripts under `tests/` only (no /tmp, no
  `python -c` one-liners), under timeout:
  - `python3 -m tests.probes.bls.test_kr_r4_audit` → must stay CLEAN
  - `python3 -m survey --folder samples/validation` → must end **SUCCESS** (no
    verified non-equivalent answer; spot timeouts / size explosions are not failures)
- When comparing languages, report containment direction + witness word
  (`python3 -m survey.diff.ltl_diff`), not just equivalence.
- Debug method: ground sub-terms against GT automata built from D's semiautomaton
  (`tests/bls/trace_fin_semantics.py` pattern), find the first diverging sub-term,
  fix against the paper text.
- Keep files roughly under 500 LOC (technical cores like the mutually-recursive
  formula cluster or parsers may exceed).

## Working style (how the user wants me to operate)
- **Diagnostics self-bound, ≤15s PER EXAMPLE.** Hard cap on any test/diagnostic
  run; a blown timeout IS a finding, report it. The cap is per example — do NOT
  batch many cases into one run to dodge it (give probes a single-input argv and
  invoke once per case). Redirect long output to `tests/**/logs/` (never /tmp),
  don't pipe long runs to `tail`.
- **No manual process management.** Never `kill`/`pkill`, no `&`/`nohup`/`$!`, no
  inspecting pids. For long self-terminating runs use the Monitor tool or Bash
  `run_in_background` (the harness tracks the task and re-invokes on completion);
  wait on completion events, never sleep/poll loops.
- **Spot is bounded-or-skipped, never waited on** in the construction/test path —
  no unbounded external calls; Spot is for hash-consing (+ the bounded oracles
  already accepted). A stall is reported, not blocked on.
- **Honest failure attribution.** Distinguish what WE failed at (a crash, a
  construction timeout with no DAG) from what a downstream tool can't handle (Spot
  hitting >32 acceptance sets, the flat form exploding). A DAG we built that Spot
  can't verify is NOT our failure.
- **Present intermediate results.** Stop and show results after each step; do not
  start a new direction without user validation.
- **Trust the scripts.** Existing scripts the user points me at and tells me to
  run are meant to be run, not to be read. Trust that the default flags do the
  job, at most `head` the script to see its pydoc. Avoid poisoning context by
  reading code we are not editing.
- **Type the signatures.** Add explicit Python type annotations (params + return)
  on new/touched functions — the user comes from Java/C++. Use `typing`
  (`Optional`/`Callable`/`Protocol`/forward-ref strings), `TYPE_CHECKING` for
  annotation-only imports; `Protocol` for behavioral contracts (see `Translator`).
