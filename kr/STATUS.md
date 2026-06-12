# kr/ Current Status

Factual snapshot of the current state. History lives in `git log`; work items in
`kr/TODO.md`; doc map in `kr/README.md`.

**Bottom line: the FoSSaCS'22 construction is implemented end-to-end and
semantically validated.** The five reachability formulas are the literal paper
forms over a genuine SgpDec holonomy cascade; the MP-class ladder shows zero
semantic failures up to the 3-level dev guard. The open front is no longer
fidelity — it is output representation and verification at scale: the
construction produces small hash-consed DAGs in fractions of a second, and
everything expensive (Spot translation, flat strings) is an artifact of
unfolding that DAG.

## Pipeline

- `decompose_aut`: Spot norm to det complete min-even parity with **state-based
  acceptance** (`sbacc` — soundness requirement: the Muller condition is lifted
  over configurations, so the infinitely-visited state set must determine
  acceptance) → generators (explicit 2^|AP| letters) → GAP/SgpDec holonomy →
  parsed `Cascade`.
- **True-cascade extraction.** The GAP script emits (i) state lifts via
  `AsHolonomyCoords(s, sk)`; (ii) the genuine transitions: generators lifted
  with `AsHolonomyCascade` acting via `OnCoordinates`, BFS-closed from the
  lifts (TRANS lines); (iii) the cover map π via `AsHolonomyPoint` (PI lines).
  Holonomy coordinatization is a many-to-one **cover**: the closure can be
  strictly larger than the lift image (duplicated sinks etc.), and config
  dynamics must come from these lifted transitions — they are NOT the
  h-conjugation of D (that shortcut yields non-reset "cascades"; soundness
  precondition checkable with `probe_reset_consistency.py`). Parse REVERSES
  coordinates: SgpDec is top-first (deeper levels read upper state), the
  operators peel index 0 first with the suffix as the self-contained
  sub-cascade. GAP RNG is seeded → decompositions are reproducible.
- `Cascade`: levels, state↔config (1-based), letter valuations, `move_config`
  (explicit transition table; legacy h-conjugation only as fallback for old
  outputs), Enter/Stay/Leave helpers, pruned config automaton, accepting
  configs. `config_to_state` is π (total on the closure); `state_to_config`
  is the lift section.
- Good Muller sets: enumeration of strongly-connected **accepting subsets** of
  non-rejecting SCCs of the pruned config aut (`acc().accepting(in-M edge-mark
  union)` oracle, exact under sbacc; `KR_MULLER_SCC_LIMIT=12` gate, logged
  whole-SCC fallback).
- Stability: `bdd_utils` buddy-var precompute + per-case subprocess isolation
  in tests.

## Operators — literal paper forms, fast

- All five formulas are the literal constructions of paper Sec 4.2 /
  construction-ref §7: solid⁺ last-step decomposition with combined letters
  ⟨σ,T'⟩ over all closure configs and Leave-avoid/bad-predecessor conjuncts;
  Formula 5 lines (1)+(2)+(3) with the swapped wsolid in line (2) and no s==t
  guard; `reach_weak` = the literal dual ¬reach(S,T,τ,B,β); literal
  wsolid/wsolid⁺; `fin_c` per Lemma 7 with ι==C postponement. Case dispatches
  compare FULL configs.
- **Hash-consed `spot.formula` objects end-to-end, INCLUDING the output**:
  `reconstruct_ltl_paper_style` / `reconstruct_ltl_1level_buchi` return the
  formula DAG (str accepted at entry for probes). Flattening is opt-in only:
  `reconstruct_ltl_str` (historical entry), or the size-gated `_str_f_gated`
  (`KR_FLATTEN_TREE_LIMIT`). `PAPER_MAX_LTL_SIZE` now reports unfolded-tree
  node count, not string chars. The non-Muller `build_phi` string sketches
  were deleted (NotImplementedError → TODO P1).
- **Fully memoized:** `reach_strong` (lru) AND the five helpers (decorator
  keyed ⟨helper, casc, S, B, β, T, τ, level⟩) — one expansion per distinct
  subproblem, BDD-style. The runaway guard counts DISTINCT subproblems
  (`KR_REACH_GUARD`, default 5M).
- **Letter fusion (2026-06-12, the "B" iteration — dag_folding.md
  counter-measure B, default ON, `KR_FUSE_LETTERS=0` restores the
  per-letter literal shape).** At every enumeration site (solid⁺/wsolid⁺
  last-step/leave/bad-pre, dashed enter_t/enter_b/line-3, fin's
  `_uncond_reach_strict`) the summand reads the letter only through its
  guard, so letters are grouped by the `_dedupe` key minus `li`
  (enter sites key on the arrival too) and each group emits ONE summand
  whose guard is the Minato-minimized OR (`_fuse_or` in ltl_builders:
  BDD round-trip via `spot.formula_to_bdd`/`bdd_to_formula`,
  process-lifetime bdd_dict, plain-Or fallback). One tail per outcome
  class instead of per letter — the distinct-tail driver shrinks at the
  source. Soundness argument: dag_folding.md "Letter fusion". Measured:
  `XXa`/`XXXa` collapse to the LITERAL formulas (3/4 tree nodes; XXXa was
  SPOT_TIMEOUT); `Xa` output is `Xa`; `G(a->Xb)` tree 3.6M→22.6k and
  distinct temporal 226→85 (under the 32-acc-set cap → equiv=True);
  `G(p->(qUr))` tree 84.8M→55k, 559→121; `G(a->Xa)` 5.1×10¹¹→11.3M;
  `(a U b)|Gc` 2⁶⁰-saturated→528M; `X(a&Xa)` 6.3×10¹³→3.1×10¹⁰ (the
  remaining ladder wall). Survey: 3 cases flipped to True (`XXXa`,
  `G(a->Xb)`, `Ga|Gb`), zero regressions; grounding: zero contradictions;
  audit CLEAN. Post-fusion log: `kr/testing/logs/fusion_measure_dag_*`.
- **Own rewrite pass wired (2026-06-12, the "1c" iteration — kr/simplify/
  package, KR_SIMP_OWN=1 default, size cap KR_SIMP_OWN_LIMIT=2000,
  KR_SIMP_OWN_FACTOR toggles rule 3).** Three rules Spot lacks (validated
  standalone 44/44 + 1500-formula random fuzz ALL EQUIVALENT, oracle
  self-tested): (1) context pass — sibling-context propagation over the
  boolean skeleton, identity domination incl. temporal nodes, Shannon at
  Or, reset at temporal boundaries; (2) now-evaluation — one-step unroll
  of G/F/U/R/W/M heads under boolean context (initial-state knowledge,
  Bonneland et al. lineage), two-tier entailment (identity + BDD);
  (3) sound partial factoring + Minato guard groups. Hooked per node in
  `_simp_f` after Spot's pass (one bounded Spot re-pass when rules fire);
  persistent package memos make it amortized O(1) per distinct node; ONE
  shared bdd_dict per process (a second dict next to the fusion one
  corrupted the equiv-child heap). The size cap exists because the
  uncapped pass sent 3 reactivity cases CONSTRUCT_TIMEOUT — capped, all
  construction times are healthy. Measured (capped, vs post-fusion):
  `Ga`→`a & G(!a|Xa)`, `Fa`→`a | F(!a&Xa)`, `a&Xa`→literal `a & Xa`;
  `G(a->Xb)` tree 22.6k→12.2k; `G(p->(qUr))` 55k→38.7k; `G(a->Xa)`
  11.3M→2.0M; `(aUb)|Gc` 528M→7.7M; giants barely move under the cap
  (`X(a&Xa)` 31G→27.9G). Survey 24 True / 0 FALSE; audit CLEAN; grounding
  zero contradictions. KNOWN regression: rewriting creates temporal-body
  VARIANTS that coexist across branches, raising the distinct-eventuality
  census — `F(a&Xb)` went back over the 32-acc cap (its equiv child then
  dies in the abort path's teardown: `free(): invalid pointer` — infra,
  not semantic). Refinement item: eventuality-aware rewriting (TODO 1c).
- **Per-DAG-node memoized simplification (2026-06-12, the "A" iteration).**
  `_simp_f` simplifies each hash-consed node ONCE (id-keyed memo + the shared
  tl_simplifier's internal cache); operators build bottom-up so every call
  sees already-simplified children. Policy `KR_SIMP_OPTS`: hybrid (default) =
  Spot's full rules only on nodes with unfolded size ≤ `KR_SIMP_FULL_LIMIT`
  (2000), basics (constant folding, X(0)→0) above — full's syntactic-
  implication pass is pairwise and sharing-blind and stalled >15s per-node on
  `X(a&Xa)`, basics never stalls. `KR_SIMP_NODE=0` = old identity behavior.
  Paired with the dead-tail early-out in reach_strong
  (`reach(…,τ≡false) ≡ false`, the Table-1 base case), folded tails delete
  their memo-key subtrees. Measured: `a&Xa` 752→311 subproblems; `G(a->Xb)`
  distinct temporal 538→226, unfolded tree 85.5M→3.6M; `G(p->(qUr))`
  distinct temporal 4115→559 (7.4x); `X(a&Xa)` max tail 177x smaller (counts
  −20% only — the residual is genuine b^k wrapping, see dag_folding.md).
  We still never WAIT on Spot: each call is one node with simplified
  children, and the escape hatch drops Spot from the path entirely.

## Validation state

The ≥4-level dev guard is GONE (opt-in `KR_MAX_LEVELS` ceiling remains; the
real runaway protection is the distinct-subproblem guard). Depth ladder
added: `Xa` 3L → `XXa` 4L → `XXXa` 5L → `X(a & Xa)` 5L.

- **MP ladder: 24 equiv=True, zero equiv=FALSE** (post fusion + own
  rewrite pass) — including **`XXXa` at 5 levels** and
  **`G(a->Xb)`/`Ga|Gb`** end-to-end. Non-True split, all
  verification-bound, none semantic:
  - SPOT_TIMEOUT: `G(a->Xa)` (2.0M, now under the flatten gate — Spot
    slow), `(a U b)|Gc` (7.7M).
  - 32-acc: `F(a&Xb)` (own-pass variant diversity — see the 1c bullet;
    the err string is the abort-path teardown crash in the child).
  - UNVERIFIED_SIZE (flatten gate): `X(a&Xa)` 2.8×10¹⁰, `GFa&GFb`
    1.1×10¹⁷, `FGa|FGb` / `(GFa&FGb)` 2⁶⁰-saturated.
- **Semantic grounding (`trace_fin_semantics`, cover-aware — GTs on the config
  semiautomaton): zero contradictions across every probed case at every
  depth** (`GFa`, `a U b`, `Fa & Gb`, `Ga | Fb`, `Xa` fully OK; `G(a->Xb)`,
  `Ga|Gb`, `F(a&Xb)`, `G(p->Xq)`, `G(p->(qUr))`, `XXXa` 14 OK, `X(a&Xa)`
  11 OK — remaining sub-terms UNVERIFIED by size only). Every check Spot can
  complete is OK.
- Audit gate (`test_kr_r4_audit.py`): CLEAN.

## Open front: representation & verification at scale (not fidelity)

Full analysis, thesis and candidate counter-measures: `kr/dag_folding.md`
(research notes, deliberately open). Summary: the construction is cheap; the
flat form is not. Current measurements (`measure_formula_dag.py`):

| case | build | DAG nodes | unfolded tree | sharing |
|---|---|---|---|---|
| `G(a->Xb)` | 0.08s | ~1.2k | ~1.5M | >1200x |
| `Ga\|Gb` | 0.08s | ~1k | 2M | >2000x |
| `G(p->(qUr))` | 0.14s | 9k | 64.8M | 7179x |
| `(a U b)\|Gc` | 9.5s | (284k subproblems) | — | — |

Consequences: (i) Spot translation hits the 32-acceptance-set tableau limit
(one set per distinct temporal subformula; we carry 100s–1000s) or times out;
(ii) flat strings reach 100MB+ (one `G(p->(qUr))` fin sub-term: 108MB), so
the str() API contract itself becomes the bottleneck for the biggest cases.
All test scripts carry built-in Spot budgets (`KR_SPOT_EQUIV_TIMEOUT` /
`KR_CHECK_TIMEOUT`, 10s) and report SPOT_TIMEOUT / UNVERIFIED — never
conflated with semantic failure. Spot authors are in the loop on
sharing-aware translation (our outputs are the ideal client). The active work
items (TODO P0): our own sharing-aware fold pass, compositional +
word-sampling verification.

**Object-out API landed (P0 plumbing item, 2026-06-12).** With reconstruct
returning the DAG and harnesses flattening only under `KR_FLATTEN_TREE_LIMIT`
(survey default 5M tree nodes ≈ every case Spot equiv ever completed), the
former CONSTRUCT_TIMEOUT class became measured verdicts in seconds:
`G(a->Xa)` ~2k DAG nodes unfolding to **5.1×10¹¹** tree nodes (sharing
~2.5×10⁸); `(a U b)|Gc` saturates the counter at 2⁶⁰. Previously-True ladder
cases re-verified True; audit CLEAN.

**Native-operator basis: investigated and CLOSED (2026-06-12,
`probe_native_ops` — one-shot tool, lives in git history).** The former
"raw U sugar" observation was stale, pre-iteration-A. Measured: Spot's
constructors do NOT rewrite sugar (`U(1,a)` and `¬(a U b)` stay raw nodes),
but the per-node simplifier normalizes every node to negation normal form
even in basics-only mode (`¬(1 U ¬a)`→`Ga`, `¬(b U ¬a)`→`¬b R a`); since
the operators build bottom-up through `_simp_f`, **outputs are already in
the native G/F/R/W basis** — census of real outputs shows `Not` only over
atomic propositions, zero ¬-over-U anywhere. The surviving U nodes are
GENUINE strong eventualities (distinct `¬β U τ` base cases): 94 in
`G(a->Xb)`, 246 in `G(p->(qUr))` — the >32-acc-set driver is the genuine
eventuality count, which no operator-basis change can reduce. Reduction
must come from folding (TODO 1 B/C/D) or non-translation verification
(TODO 3). Baseline size censuses for the standard cases:
`kr/testing/logs/baseline_*_2026-06-12.txt`.

**Object-path translation is a dead end (probed 2026-06-12,
`probe_object_translate.py`).** Spot accepts our formula objects natively
everywhere (`ltl_to_tgba_fm`, `translate`, `translator` class — no string
round-trip), but Couvreur allocates one acceptance set per DISTINCT
eventuality: our 400–600 distinct temporal subterms blow the compile-time
`mark_t` cap (32 in system Spot 2.14.5) instantly, and `Ga|Gb` ground >10s in
the tableau before even reaching the cap — the tableau's state space is sets
of subformulas, which hash-consing does not shrink. Verification must come
from word sampling / compositional grounding (TODO P0), or from folding the
eventuality count itself below the cap.

## Tooling for targeted work

All under `kr/testing/` (placed scripts only; subprocess isolation; small
built-in budgets — a blown budget is a finding, not a nuisance).

**One-shot probe lifecycle (cleanup 2026-06-12):** a probe built to answer
ONE question is committed, its finding recorded here, then deleted — git
history keeps it. Removed in that sweep: `probe_object_translate` (finding
above), `probe_native_ops` (native-basis closure above), `probe_2l_rwith`,
`probe_sbacc` (sbacc is baked into the pipeline), `test_kr_arch_adopt`
(architecture adopted), `test_kr_muller` (Muller handling settled in
`config_graph`), `diag_stability` (per-case subprocess isolation is now
standard in every script). Dead code swept from the core the same day:
unused `_F`/`_G` sugar builders (outputs get native F/G via `_simp_f` NNF),
and the never-read legacy 7-tuple `_reach_memo` write in `reach_strong`
(`_reach_memo` itself stays — `fin.py` caches through it).
`kr/testing/logs/` holds committed baseline size censuses for before/after
comparison of fold work.

- `survey_mp_cascade.py` — MP-class × depth ladder; construction and
  Spot-equiv phases in separate subprocesses with separate budgets
  (`KR_CONSTRUCT_TIMEOUT` 30s / `KR_SPOT_EQUIV_TIMEOUT` 10s).
- `trace_fin_semantics.py` — per-config semantic grounding of fin_c sub-terms
  vs GTs on the config semiautomaton (cover-aware), witness words, per-check
  subprocess cap (`KR_CHECK_TIMEOUT`); verdicts OK/BAD/UNVERIFIED; prints
  truncated; >2MB sub-terms fast-skipped.
- `probe_reset_consistency.py` — soundness precondition: every combined letter
  acts identity-or-reset per level under both context conventions.
- `probe_sgpdec_api.g` — hand-run GAP ground truth for the SgpDec bridge calls
  (lift/π inversion, morphism property, closure).
- `probe_memo_stats.py` — memo profiler: distinct subproblems vs raw calls,
  helper-memo size, alarm + watchdog stack dump (names the native call when
  stuck in C++).
- `measure_formula_dag.py` — DAG vs string size of the assembled formula
  (now measuring the real reconstruct output); `--no-str` to measure cases
  whose flat form is 100MB+.
- `probe_tail_anatomy.py` — per-level dissection of the helper memo:
  subproblem counts by operator tag, DISTINCT tails/betas/(S,B,T) triples,
  tail-size quartiles, tail growth ratios. The tool that showed tails (not
  the avoid web) drive the explosion and measured the A-iteration.
- `probe_case_diff.py` — containment + witness for one full roundtrip,
  in-process build + fresh diff child via stdin (multi-MB formulas can't
  ride argv).
- `ltl_diff.py` — containment direction + witness words.
- `test_kr_r4_audit.py` — structural checklist + drift grounding (gate for
  operator commits).
- `test_kr_zoom.py` / `test_kr_reconstruct.py` — single-case full trace /
  multi-case roundtrip with isolated equiv.
