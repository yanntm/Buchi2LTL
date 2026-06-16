# aut2ltl — Project TODO

Open project-level items only. Engine work items live in `aut2ltl/kr/TODO.md`;
the record of completed campaigns is in git history and `docs/HISTORY.md`.

## ACTIVE CAMPAIGN: migrate all contract impls onto `aut2ltl/result.py`

**Why.** We introduced a clean result lifecycle — spec in `aut2ltl/result.md`,
impl in `aut2ltl/result.py`: a closed `Status` enum (`OK`/`DECLINED`/`NOT_LTL`)
and a `Result` accumulator with `start`/`success`/`decline`/`not_definable`,
`credit`/`fuse` (composition monoid, OK identity) and `first`/`decline` (choice
monoid, decline identity). `aut2ltl/sl/sl_core.py` is the proven test subject.
Now migrate every other producer/combinator off the legacy
`aut2ltl/contract.py::LTLFormulaResult` onto `Result`, then retire it.

**Reference example (copy this pattern).** `aut2ltl/kr/buchi.py` (commit pending):
- import: `from aut2ltl.contract import CascadeTranslator` + `from aut2ltl.result import Result`
- `LTLFormulaResult.decline()` → `Result.decline()`
- `LTLFormulaResult(formula=res, technique={self.name})` → `Result.success(res, self.name)`
- annotate `__call__ -> Result`.
For a consumer that folds children, use the accumulator idiom (see `sl_core.py`):
`res = Result.start(name)`, `res.credit(child)`, `if res.nok: return res`, then
set `res.formula = ...` and return. `credit` is duck-typed so it also accepts a
legacy `LTLFormulaResult` during migration (reads `.ok/.declined/.not_ltl/.technique`).

**Status model change (decided).** Collapse `PROBABLY_NOT_LTL` into a single
`NOT_LTL` status; the proof-vs-hint wording moves into the `diagnosis` text. So
`LTLFormulaResult.not_ltl_definable(conclusive=, note=)` →
`Result.not_definable(diagnosis=<wording incl. conclusive/hint>)`. Drop
`.conclusive` branches; `.note` → `.diagnosis`. `first` rule is the single
`if not r.declined: return r` (OK or NOT_LTL stop; only DECLINED continues).

**Checklist** (do one at a time; each fits the pattern; gate at the end):
1. [DONE] kr leaf producers → Result: `buchi.py` ✅, `acc.py` ✅, `weak.py` ✅,
   then `cobuchi.py`, `bls.py` (same edit).
2. [ ] `aut2ltl/kr/aut2cas.py` `as_translator`: gate returns
   `Result.not_definable(diagnosis=...)` folding the conclusive/hint wording;
   annotate `-> Result`.
3. [ ] `aut2ltl/combinators.py` `first_success`: terminal `Result.decline()`;
   condition `if not r.declined: return r`. Keep the named wrapper (build.py /
   hierarchy_class.py pass `name=`).
4. [ ] `aut2ltl/portfolio/decompose.py`: Result + credit/fuse for AND/OR
   recombine; replace `tech |= s.technique`; the conclusive-pick
   (`next((s for s in not_ltls if s.conclusive), ...)`) → just propagate the
   first NOT_LTL; `s.declined or s.formula is None` → `not s.ok`.
5. [ ] `aut2ltl/portfolio/sl_driven.py`: Result + credit; `r.declined or
   r.formula is None` → `not r.ok`; accumulator idiom for the final.
6. [ ] `aut2ltl/portfolio/sl.py`: return Result; `out.declined or out.formula is
   None` → `not out.ok`; `set(out.technique or {name})` → credit. (interop with
   legacy reconstruct_ltl until #7).
7. [ ] `aut2ltl/sl/reconstruction.py` (legacy engine, biggest): line ~336-337
   `LTLFormulaResult(final, techset)` / `.decline(techset)` → Result. Behavior
   identical; gate with survey.
8. [ ] `aut2ltl/contract.py`: point `Translator`/`CascadeTranslator` annotations
   at `Result`; remove `LTLFormulaResult` + the status-string constants once no
   producer constructs it; update remaining `from aut2ltl.contract import
   LTLFormulaResult` imports. (Settle: keep protocols here vs move; file is
   poorly named.)
9. [ ] `aut2ltl/__main__.py`: lines ~204-208 — drop `res.conclusive`, print
   single `NOT_LTL` + `res.diagnosis`; `res.declined or res.formula is None` →
   `not res.ok`. Keep a token `tests/survey.py` can detect (it greps stderr for
   `NOT_LTL`/`PROBABLY_NOT_LTL` at survey.py:218,331 — update survey if the
   `PROBABLY` label is dropped).
10. [ ] Gates: `python3 tests/kr/test_kr_r4_audit.py` CLEAN; `python3
    tests/survey.py` SUCCESS. Then this campaign is done — delete this block.

**Migration probes** (already green, keep using): `tests/sl/probe_sl_core.py`
(pure sl), `tests/sl/probe_sl_over_str.py` (sl over kr `str`, X-prefixed).

## Open

- **Output size at scale (the live research front).** The construction is cheap;
  the cost is the flat form — Spot hits its 32-acceptance-set tableau limit and
  the largest flat strings explode. This is representation/verification, not
  fidelity. Analysis and candidate counter-measures: `docs/dag_folding.md`.

- **`best_of` combinator.** The portfolio optimizes for the FIRST success, not the
  smallest output — but size is the research objective. Add `best_of([...],
  key=cost)` beside `first_success`, plus a `cost`/size field on
  `LTLFormulaResult` (the dataclass is pre-shaped for it). Until then, cited order
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
