# BuchiToLTL — Working Notes for Claude

## Orientation (don't duplicate here — follow the pointers)
- `kr/README.md` — entry point: doc map, pipeline, module map, testing tools.
- `kr/STATUS.md` — current state + the failing-case ladder. `kr/TODO.md` — work items.
- `paper/automata-to-ltl-construction.md` — the construction reference.
- `paper/Automata2LTL.txt` — ground truth for any formula-fidelity question
  (Sec 4.2 + Table 1 + Formulas 3/4/5 ≈ lines 440–1040). LLM summaries have twice
  introduced guard/case errors; the paper text settles disputes.
- `buchi2ltl/` is the separate heuristic path (backward labeling + f2/t2 SCC
  heuristics). The paper construction is now stable, so it is WIRED INTO the kr
  decompose dispatcher as a sound pre-filter gate — but ONLY through the single
  seam `kr/heuristic_gate.py` (tried per node in `decompose_recombine`); the kr
  core operators stay pure and import nothing from `buchi2ltl/`.

## Discipline (mandatory)
- One file per commit (logical moves excepted); no commit without explicit user approval.
- Update STATUS/TODO *before* committing a code change.
- Test BEFORE commit, via placed scripts under `kr/testing/` only (no /tmp, no
  `python -c` one-liners), under timeout:
  - `python3 kr/testing/test_kr_r4_audit.py` → must stay CLEAN
  - `python3 kr/testing/survey_mp_cascade.py` → previously-True cases must stay True
- When comparing languages, report containment direction + witness word
  (`kr/testing/ltl_diff.py`), not just equivalence.
- Debug method: ground sub-terms against GT automata built from D's semiautomaton
  (`kr/testing/trace_fin_semantics.py` pattern), find the first diverging sub-term,
  fix against the paper text.
- Keep files roughly under 500 LOC (technical cores like the mutually-recursive
  formula cluster or parsers may exceed).
