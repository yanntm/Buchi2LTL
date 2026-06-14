# BuchiToLTL — Working Notes for Claude

## Project layout (P-ARCH, nested root package `aut2ltl/`)
Layering, acyclic: `aut2ltl/contract.py` (ReconResult/Translator floor) ←
`aut2ltl/kr` (pure cascade FoSSaCS engine) + `aut2ltl/sl` (heuristic engine,
ex-`buchi2ltl/`) ← `aut2ltl/portfolio` (combinators: decompose / gate /
sl_driven) ← `aut2ltl/cli` + `__init__`. Tests live under `tests/` (`tests/kr`,
`tests/sl`, `tests/fixtures`). See `aut2ltl/kr/TODO.md` "THE MOVE CAMPAIGN".

## Orientation (don't duplicate here — follow the pointers)
- `aut2ltl/kr/README.md` — entry point: doc map, pipeline, module map, testing tools.
- `aut2ltl/kr/STATUS.md` — current state + the failing-case ladder.
  `aut2ltl/kr/TODO.md` — work items.
- `paper/automata-to-ltl-construction.md` — the construction reference.
- `paper/Automata2LTL.txt` — ground truth for any formula-fidelity question
  (Sec 4.2 + Table 1 + Formulas 3/4/5 ≈ lines 440–1040). LLM summaries have twice
  introduced guard/case errors; the paper text settles disputes.
- `aut2ltl/sl/` is the separate heuristic engine (backward labeling + f2/t2 SCC
  heuristics). It is wired into the decompose dispatcher as a sound pre-filter
  gate — but ONLY through the single seam `aut2ltl/portfolio/heuristic_gate.py`
  (tried per node in `aut2ltl/portfolio/decompose_recombine.py`); the kr core
  operators stay pure and import nothing from `aut2ltl/sl/` (only the contract).

## Discipline (mandatory)
- One file per commit (logical moves excepted); no commit without explicit user approval.
- Update STATUS/TODO *before* committing a code change.
- Test BEFORE commit, via placed scripts under `tests/` only (no /tmp, no
  `python -c` one-liners), under timeout:
  - `python3 tests/kr/test_kr_r4_audit.py` → must stay CLEAN
  - `python3 tests/kr/survey_mp_cascade.py` → previously-True cases must stay True
- When comparing languages, report containment direction + witness word
  (`tests/kr/ltl_diff.py`), not just equivalence.
- Debug method: ground sub-terms against GT automata built from D's semiautomaton
  (`tests/kr/trace_fin_semantics.py` pattern), find the first diverging sub-term,
  fix against the paper text.
- Keep files roughly under 500 LOC (technical cores like the mutually-recursive
  formula cluster or parsers may exceed).
