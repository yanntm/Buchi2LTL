# aut2ltl — Working Notes for Claude

## Project layout (nested root package `aut2ltl/`)
Layering, acyclic: `aut2ltl/contract.py` (LTLFormulaResult/Translator floor) +
`aut2ltl/language.py` ← `aut2ltl/kr` (pure cascade FoSSaCS engine) +
`aut2ltl/sl` (heuristic engine, ex-`buchi2ltl/`) ← `aut2ltl/portfolio`
(combinators: build / decompose / gate / sl_driven) ← `aut2ltl/__main__` +
`__init__`. Engine-agnostic helpers in `aut2ltl/ltl` (metrics, printers,
simplify). Tests under `tests/` (`survey*`, `tests/kr`, `tests/sl`,
`tests/fixtures`).

## Orientation (don't duplicate here — follow the pointers)
- `README.md` — repo guide / quick start. `STATUS.md` / `TODO.md` — project
  snapshot / open items.
- `aut2ltl/kr/README.md` — kr engine entry point: doc map, pipeline, module map,
  testing tools. `aut2ltl/kr/STATUS.md` — **current** engine state (read to start).
  `aut2ltl/kr/TODO.md` — engine work items.
- `docs/HISTORY.md` — construction log (the dated DONE/WIRED/LANDED/reverted
  record). Reference for the *why/when*; **do NOT read it to start a session** —
  STATUS.md is the current snapshot.
- `docs/algorithm.md` — the construction's scope/policy and module mapping.
  `docs/dag_folding.md` — the size-explosion analysis (open research direction).
- `paper/automata-to-ltl-construction.md` — the construction reference.
- `paper/Automata2LTL.txt` — ground truth for any formula-fidelity question
  (Sec 4.2 + Table 1 + Formulas 3/4/5 ≈ lines 440–1040). LLM summaries have twice
  introduced guard/case errors; the paper text settles disputes.
- `aut2ltl/sl/` is the separate heuristic engine (backward labeling + f2/t2 SCC
  heuristics). It is wired into the decompose dispatcher as a sound pre-filter
  gate — but ONLY through the single seam `aut2ltl/portfolio/heuristic_gate.py`;
  the kr core operators stay pure and import nothing from `aut2ltl/sl/` (only the
  contract).

## Discipline (mandatory)
- One file per commit (logical moves excepted); no commit without explicit user
  approval. Commit directly to master (the user does not branch when prototyping).
- Update STATUS/TODO *before* committing a code change.
- Test BEFORE commit, via placed scripts under `tests/` only (no /tmp, no
  `python -c` one-liners), under timeout:
  - `python3 tests/kr/test_kr_r4_audit.py` → must stay CLEAN
  - `python3 tests/survey.py` → must end **SUCCESS** (no verified non-equivalent
    answer; spot timeouts / size explosions are not failures)
- When comparing languages, report containment direction + witness word
  (`tests/kr/ltl_diff.py`), not just equivalence.
- Debug method: ground sub-terms against GT automata built from D's semiautomaton
  (`tests/kr/trace_fin_semantics.py` pattern), find the first diverging sub-term,
  fix against the paper text.
- Keep files roughly under 500 LOC (technical cores like the mutually-recursive
  formula cluster or parsers may exceed).

## Working style (how the user wants me to operate)
- **Diagnostics self-bound, ≤15s.** Hard cap on any test/diagnostic run; a blown
  timeout IS a finding, report it. Redirect long output to `tests/**/logs/`
  (never /tmp), don't pipe long runs to `tail`.
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
- **Type the signatures.** Add explicit Python type annotations (params + return)
  on new/touched functions — the user comes from Java/C++. Use `typing`
  (`Optional`/`Callable`/`Protocol`/forward-ref strings), `TYPE_CHECKING` for
  annotation-only imports; `Protocol` for behavioral contracts (see `Translator`).
