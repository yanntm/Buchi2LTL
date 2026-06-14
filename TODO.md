# aut2ltl — Project TODO

Project-level work items. Engine-level items live in `aut2ltl/kr/TODO.md`.

## RESUME HERE — kr/ CascadeTranslator refactor (2026-06-14)

We are turning `kr/` into a clean OO architecture: a contract floor, self-gating
translator *members*, and a composition combinator. Most of it is done and
pushed (master @ `b7349f5`); the **pipeline sweep is the last piece**.

### Done (pushed)
- `aut2ltl/contract.py`: `ReconResult`, `Translator`, and `CascadeTranslator`
  (Protocol with a fixed `name` — members are named, self-gating callables).
- `aut2ltl/combinators.py`: `first_success([...])` — the chain composite
  (try in order, first OK wins, else decline), generic over the input type.
- kr leaves are now **CascadeTranslator members, one per file**, each self-gating
  (returns a faithful `ReconResult` or declines) and stamping `technique={name}`:
  `kr/acc.py` (Acc/acc, bounded fragment), `kr/buchi.py`, `kr/cobuchi.py`,
  `kr/weak.py`, `kr/bls.py` (general Muller-DNF fallback). Predicates
  `is_{buchi,cobuchi,weak}_cascade` live with their member.
- support: `kr/muller.py::assemble_muller_dnf` (the bls builder);
  `kr/reachability_operators.py` + `kr/fin.py` (the 5 reach formulas + `fin_c`,
  the mutually-recursive core); `reset_build_state` lives there now.
- `kr/cascade/` is a **package**: `model.py` (Cascade), `config_graph.py`
  (analysis + relocated `good_muller_sets`), `__init__.py` re-exports.
- tests: `tests/test_contract_combinators.py`, `tests/kr/test_acc_translator.py`.

### Next steps (the pipeline sweep — integrate the new endpoint)
Design (refined): the ladder becomes a *configured `first_success` instance* and
the twa-level entry a *GAP adapter* — both as NEW files in `kr/`, not an in-place
collapse of `reachability.py`. The form caveat is satisfied INSIDE the members
(each self-recovers its automaton form — cobuchi/weak `postprocess(.,"generic")`,
buchi `is_buchi`, acc `original_aut`), so the chain does nothing form-specific.

1. ✅ **`first_success` is a real named translator** (`aut2ltl/combinators.py`):
   obeys the Translator/CascadeTranslator interface, `name` passed at
   construction, winning stage's ReconResult (incl. technique) forwarded
   unchanged. (The flags/options/counters cleanup is a SEPARATE pass — deferred;
   the `KR_DISPATCH_*` env knobs are left as-is for now.)
2. ✅ **`kr/hierarchy_class.py`** — the acceptance-dispatch chain as a named
   `first_success([acc,(weak),buchi,cobuchi,bls])`, default singleton
   `hierarchy_class`; the `KR_DISPATCH_*` env gates kept verbatim.
3. ✅ **`kr/aut2cas.py`** — `as_translator(ct) -> Translator` (twa →
   `decompose_aut` → cascade → member); endpoint singleton `reconstruct =
   as_translator(hierarchy_class)`. The `KR_MAX_LEVELS` depth guard is carried
   here (it was the only live part of `reconstruct_bls`).
4. ✅ **Integrated.** `kr/__init__.py` exports `hierarchy_class`/`reconstruct`;
   the functional caller (`portfolio/decompose_recombine.py`, default leaf →
   `hierarchy_class`) and the maintained survey/gate scripts (`survey_mp_cascade`,
   `survey_sizes`, `test_kr_r4_audit`) repointed to `hierarchy_class(casc).formula`;
   `reconstruct_bls`, `reconstruct_ltl_paper_style`, `build_phi` DELETED and
   `reachability.py` trimmed to the operator re-export hub. Gates GREEN on the new
   path — r4 CLEAN, MP survey 70/70 equiv=True (verdicts byte-identical to
   baseline; behaviour-preserving).
   LEFT FOR LATER (one-shot probes + secondary tests — break on import, NOT gates;
   patch or prune when next needed): the ~9 `probe_*.py`,
   `test_kr_{reconstruct,zoom,basic}.py`, `measure_formula_dag.py`.

Deferred passes (own iterations): the flags/options/**counters** cleanup (the
module-global build state in `reachability_operators.py` — see Known debt) and the
Phase-2 portfolio OO + `Language` reification (`aut2ltl/kr/TODO.md`).

### Known debt (flagged by user, deferred)
- **Module-global mutable state** in `reachability_operators.py` (counters +
  memos; `reset_build_state` is a band-aid) — bad design; move to instance/context.
- `kr/README.old` to delete once the new `kr/README.md` is settled.

### Gates & discipline (do not skip)
- Run BOTH gates **in full** before committing engine changes:
  `python3 tests/kr/test_kr_r4_audit.py` → CLEAN; and
  `python3 tests/kr/survey_mp_cascade.py` with **NO args** (all ~35 formulas) →
  every case `equiv=True`. Passing a subset of formulas SKIPS the gate — don't.
- Commit **locally only** (push only when the user says so this turn). Tests are
  **placed scripts** under `tests/` (no `python -c`). Comments **describe** what
  code does, never refactor history. One file per commit unless it is a logical
  move; the user sometimes asks for file-by-file with per-file messages.

## Other

- **Real CLI** over `reconstruct_decomposed` (current `cli.py` is an sl-only
  stub). See `STATUS.md` "CLI".
- Engine work items: see `aut2ltl/kr/TODO.md`.
- The per-file LOC inventory that used to live here is **stale** after this
  session (cascade→package, gap_bridge→gap/, acceptance_dispatch split into
  acc/buchi/cobuchi/weak/bls, etc.); regenerate on demand.
