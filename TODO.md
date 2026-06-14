# aut2ltl — Project TODO

Project-level work items. Engine-level items live in `aut2ltl/kr/TODO.md`.

## Configurability — reify the runtime context, kill the statics (active 2026-06-14)

Replace the module-global flags/statics with an explicit, threaded context — the
`OptionsCache` — built at the front end, **not a singleton**. Three compartments,
landed in SEPARATE iterations:
- **Options** (flags) — THIS iteration. An open key-value store (mostly bool).
- **Caches** (construction memos, counters) — later: fold the
  `reachability_operators` statics in; fresh on `clone`.
- **Infra** (`bdd_dict`/buddy, DAG unifier) — later: shared-ref on `clone`.

Design (settled): defaults live in the per-package `OptionSpec` (key + default +
doc + legacy env). `Options.get(SPEC)` resolves lazily — store value if set, else
`spec.default` — so a bare `Options()` is "all defaults", no pre-init / registry /
module-walking. Layering: the FLOOR declares the store (`aut2ltl/options.py`, no
engine imports); each PACKAGE declares its keys (`<pkg>/options.py` — its OPTIONS
contract + the default source); the ROOT / front end aggregates specs and layers
env/CLI/API overrides (the only place that knows all packages).

### This iteration — the Options backbone (no call-site wiring yet) — IN PROGRESS
1. ✅ `aut2ltl/options.py` (floor): `OptionSpec(key, default, doc, env)` + `Options`
   (`get(spec_or_key)` lazy default, `set`, `clone(overrides)`, `from_specs(env=)`)
   + `tests/test_options.py` (6/6 green).
2. Per-package spec declarations (real `os.environ` knobs gathered — see below):
   - ✅ `aut2ltl/portfolio/options.py` — `portfolio.sl.*` keys (the exemplar;
     naming convention set).
   - ⏳ `aut2ltl/kr/options.py` — the big one, ~18 knobs. Hierarchical sub-namespaces:
     `kr.dispatch.{acc,weak,buchi,cobuchi}`, `kr.fold_fin_reach`, `kr.fuse_letters`,
     `kr.reach_guard`, `kr.max_levels`, `kr.muller_scc_limit`, `kr.simp.*`
     (own/fold/factor/limit/node/opts/full_limit/tree_limit), `kr.flatten_tree_limit`,
     `kr.trace`. `env=` the matching current `KR_*` / `RECONSTRUCT_TRACE`.
     (`KR_SAT_MIN_STATES` is read in floor `language.py` — give it a `language.*`
     key or fold into kr; decide when wiring.)
   - ⏸ `aut2ltl/sl/options.py` — DEFERRED to the sl refactor: sl's flags are read
     in `portfolio/sl.py` today, and its f2/t2 heuristics are unwrapped `Translator`s;
     sl gets its own contract when those are wrapped.
3. ⏳ Root builder at the front end (`aut2ltl/cli.py`, "aut2ltl main"):
   `build_options(overrides=None)` = aggregate the per-package spec lists + env →
   default `Options`. Additive.

**Key naming — SETTLED:** hierarchical, meaning-based, reflecting CURRENT code
(e.g. `portfolio.sl.enabled`, not `…gate.buchi2ltl`); no backward-compat
constraints on the dotted keys. `env=` keeps the current legacy var as the seeding
bridge only.

### Deferred (separate iterations)
- **Wire call sites**: thread `Options` into Translator construction, repoint each
  `os.environ.get(...)` → `options.get(SPEC)`, ONE package at a time, survey-gated.
- **Caches compartment**: fold `reachability_operators` globals (memos, counters,
  `reset_build_state`) into the cache bucket; fresh-on-clone; removes the resets.
- **Infra compartment**: `bdd_dict`/buddy + DAG unifier as shared refs.

## Architecture refactor — DONE (2026-06-14)

The OO refactor is complete: a contract floor (`Language` + `LTLFormulaResult` +
the `Translator` / `CascadeTranslator` protocols), the kr cascade as self-gating
members composed by `hierarchy_class`, the `aut2cas` adapter lifting it to a
`Language` Translator, and the **portfolio as pure Translator composition** —
`Sl` / `SlDriven` / `Decompose` over `first_success`, default entry
`Decompose(first_success([sl_driven, cascade]))`. All gates green (r4 CLEAN, MP
survey 70/70 equiv=True). Remaining work is the deferred passes below.

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

### Done — the CascadeTranslator sweep (record)
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

Deferred passes (own iterations, agreed):
- **`best_of` combinator** — the portfolio optimizes for FIRST success, not
  smallest output (the size objective is the research goal). Add a
  `best_of([...], key=cost)` sibling of `first_success` + a `cost`/size field on
  `LTLFormulaResult` (the dataclass is pre-shaped for it). Until then, chain
  order is the only size heuristic.
- **flags/options/counters cleanup** — the module-global build state in
  `reachability_operators.py` (counters + `reset_build_state`); load-bearing under
  composition (Decompose recursing while SlDriven delegates). See Known debt.
- **`KR_DISPATCH_*` / `KR_GATE_*` env knobs** — left verbatim through the refactor;
  fold into constructor args once the above lands.
- **broken probes + secondary tests** (import the retired symbols; NOT gates):
  `tests/kr/probe_*.py`, `fuzz_gate_decompose.py`, `test_kr_{reconstruct,zoom,basic}.py`,
  `measure_formula_dag.py`. Patch or prune when next needed.

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
