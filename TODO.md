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
   - ✅ `aut2ltl/kr/options.py` — the full kr contract, all ~18 knobs grouped by
     bucket (`kr.dispatch.*`, `kr.fold_fin_reach`, `kr.fuse_letters`, `kr.reach_guard`,
     `kr.max_levels`, `kr.muller_scc_limit`, `kr.simp.*`, `kr.flatten_tree_limit`,
     `kr.trace`). `KR_OPTIONS` (full) + `KR_DISPATCH_OPTIONS` (Bucket-1 sub-list).
   - ✅ `aut2ltl/language.py` — tiny floor contract `language.sat_min_states`
     (`KR_SAT_MIN_STATES`), declared inline (single module, not a package).
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

### Wiring analysis — scope cut (2026-06-15)
Audited every `os.environ`/`getenv` read in `aut2ltl/`. Only a SMALL subset is
genuine instance config worth construct-time OO threading; the rest is process-
global by nature and STAYS env. The kr leaves are already objects (`Bls`/`Acc`/
`Buchi`/`Cobuchi`/`Weak`) and the chain is built by a builder
(`make_hierarchy_class`), so the real config sits at object/builder boundaries —
no need to thread `options` into the recursive reachability core.

**Declaration vs. wiring are separate.** A package's `options.py` is the COMPLETE
contract: it declares EVERY env knob the package reads as an `OptionSpec` (with
`env=` + `doc`), so the knobs are discoverable/self-documenting in one place — this
holds for all three buckets. The bucket split governs only WIRING effort: which
specs get their call sites repointed `os.environ.get(...)` → `options.get(SPEC)`
this iteration. A declared-but-not-yet-wired spec keeps reading `os.environ`
directly; its `default` must MIRROR the current in-code default until repointed
(the spec becomes the single source on repoint).

- **Bucket 1 — declare AND wire to construct-time Options (THIS iteration):**
  `portfolio.sl.{enabled,max_states,verify}` (all inside the `Sl` object) and
  `kr.dispatch.{acc,weak,buchi,cobuchi}` (already read at BUILD time in
  `make_hierarchy_class`, not per-call).
- **Bucket 2 — declare now; real A/B knobs but DEEP (pervasive in the recursion/
  simplifier), so LEAVE the call sites on env for now:** `KR_FUSE_LETTERS`,
  `KR_FOLD_FIN_REACH`, `KR_SIMP_OWN`/`KR_SIMP_OWN_FOLD`. Sound optimizations,
  always-on in practice, flipped only in size experiments — process scope is fine.
  Wire later only if per-instance optimization A/B is ever needed (the owning
  object passes `options` to its one call site).
- **Bucket 3 — declare now; NOT instance config, so LEAVE the call sites on env:**
  all tracing (`KR_TRACE`, `RECONSTRUCT_TRACE`, `F2_TRACE`, `T2_TRACE`); resource/
  safety limits (`KR_REACH_GUARD`, `KR_MAX_LEVELS`, `KR_MULLER_SCC_LIMIT`,
  `KR_SAT_MIN_STATES`, `KR_FLATTEN_TREE_LIMIT`, the `KR_SIMP_*` tuning thresholds).
  Process-wide scope is the correct scope; the spec just documents them.
- **Counters are NOT Options** (`PAPER_REACH_CALLS`/`_FIN_CALLS`/`_MAX_LTL_SIZE`):
  `_MAX_LTL_SIZE` is DEAD (reset, never incremented/read); `_FIN_CALLS` is pure
  profiling (read only by the `measure_formula_dag` probe); `_REACH_CALLS` is the
  runaway-guard's distinct-subproblem counter — redundant with the reach-memo size.
  → deferred to the **Caches compartment**: guard reads cache size, drop the dead
  one, demote profiling, and `reset_build_state` dies with the per-build cache.

### Step plan — Bucket 1 wiring (APPROVED 2026-06-15; steps 1–4 DONE, gates green; step 5 deferred)
Steps 1–4 landed; all gates green on the wired tree (options test 7/7, r4 audit
CLEAN, MP survey 70/70 equiv=True — verdicts identical to baseline). Bucket 1 now
reads from the injected `Options`; module singletons stay env-seeded defaults.
Threading model: each Translator takes `options: Optional[Options] = None` at
construction; `None` ⇒ a default built from that package's specs with the env
bridge (`Options.from_specs(<specs>)`), so bare `Sl()` / the module singletons
behave EXACTLY as today (env still honored — surveys' subprocess A/B unaffected).
The assembled graph threads ONE shared `Options` to every node. Semantic shift
(stated, intended): per-call env reads become per-instance frozen.

One file per commit; both gates (r4 audit CLEAN + MP survey all equiv=True) before
each commit that touches a translator.

1. `aut2ltl/kr/options.py` (NEW) — the COMPLETE kr contract: declare ALL kr env
   knobs as `OptionSpec`s (Buckets 1+2+3), grouped/commented by bucket, each
   `env=` its current `KR_*`/`RECONSTRUCT_TRACE` and `default` MIRRORING the
   in-code default. Export a `KR_OPTIONS` list (all) and a `KR_DISPATCH_OPTIONS`
   sub-list (the Bucket-1 dispatch specs the builder threads now). `KR_SAT_MIN_STATES`
   lives in floor `language.py` — give it a `language.*` spec (own tiny
   `language/options.py` or a `LANGUAGE_OPTIONS` here; decide at write time).
   Extend `tests/test_options.py` if useful.
2. `aut2ltl/kr/hierarchy_class.py` — `make_hierarchy_class(options=None)` reads
   `options.get(DISPATCH_*)` (default `Options.from_specs(KR_DISPATCH_OPTIONS)`);
   drop the four `os.environ.get` reads. Singleton built with the default. GATE.
3. `aut2ltl/portfolio/sl.py` — `Sl(options=None)` reads `SL_ENABLED/MAX_STATES/
   VERIFY` from `options` (default `Options.from_specs(PORTFOLIO_OPTIONS)`); drop
   the module `_MAX_STATES` const and the three `os.environ` reads. GATE.
4. `aut2ltl/portfolio/__init__.py` — build ONE shared default `Options`
   (`from_specs(PORTFOLIO_OPTIONS + KR_OPTIONS)` — seed the env bridge for the full
   contract even though only Bucket 1 is consulted via `options.get` yet); construct the graph with
   it: `Sl(options)`, `make_hierarchy_class(options)` → `as_translator(hc)` for the
   cascade, threaded through `Decompose`/`SlDriven`. GATE.
5. (defer to next iteration) Root `build_options()` in `cli.py` (TODO step 3) — the
   front end that aggregates specs + layers CLI/API overrides. Out of scope here.

### Deferred (separate iterations)
- **Wire call sites**: thread `Options` into Translator construction, repoint each
  `os.environ.get(...)` → `options.get(SPEC)`, ONE package at a time, survey-gated.
- ✅ **Caches compartment** (DONE 2026-06-15): the `reachability_operators` globals
  (the reach/helper memos, the `id(casc)` registry, the `PAPER_*` counters) and
  `reset_build_state` are GONE — folded onto a per-build `CascadeHolder`
  (`kr/cascade/holder.py`): a pure `Cascade` wrapped with `reach_memo`/`helper_memo`/
  `uncond_memo` + `reach_calls`/`fin_calls`, `__getattr__`-delegating to the cascade.
  The holder is created once per build in `aut2cas` and threaded as the
  CascadeTranslator input (the floor forward-ref now names `CascadeHolder`). A fresh
  holder IS the reset, which also fixed the `id(casc)`-reuse hazard and the
  acc/bls-don't-reset inconsistency. `PAPER_MAX_LTL_SIZE` (dead) deleted; the runaway
  guard reads `holder.reach_calls`. No module mirror for the metric — callers that
  want it create/hold the holder (gates do). Gates green: r4 CLEAN, MP survey 70/70.
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
- ✅ **counters/caches cleanup** (DONE 2026-06-15) — the module-global build state in
  `reachability_operators.py` (memos + counters + `reset_build_state`) moved onto the
  per-build `CascadeHolder`. See the Configurability "Caches compartment" entry.
- ✅ **`KR_DISPATCH_*` / `KR_GATE_*` env knobs** (DONE 2026-06-15) — now read from an
  injected `Options` at construction (Bucket 1); the env vars are the seeding bridge.
- **broken probes + secondary tests** (NOT gates) — import retired symbols (`PAPER_*`,
  `reset_build_state`) or call the reach operators with a raw `Cascade` (they now take
  a `CascadeHolder`): `tests/kr/probe_*.py`, `fuzz_gate_decompose.py`,
  `test_kr_{reconstruct,zoom,basic}.py`, `measure_formula_dag.py`. Patch (wrap in
  `CascadeHolder`, read counts off it) or prune when next needed.

### Known debt (flagged by user, deferred)
- ✅ **Module-global mutable state** in `reachability_operators.py` (counters +
  memos; `reset_build_state`) — RESOLVED 2026-06-15: moved onto the per-build
  `CascadeHolder` (see Configurability "Caches compartment").
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
