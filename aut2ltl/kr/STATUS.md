# aut2ltl/kr — Current Status

Factual snapshot of the **current** state — read this to start a session.
Construction history (the dated "DONE / WIRED / LANDED / reverted" log) lives in
`docs/HISTORY.md`; work items in `TODO.md`; doc map in `README.md`; research
notes in `dag_folding.md`.

**Bottom line: the FoSSaCS'22 construction is implemented end-to-end and
semantically validated.** The five reachability formulas are the literal paper
forms over a genuine SgpDec holonomy cascade; with the portfolio (decompose +
the buchi2ltl/sl gate over the acceptance-dispatch cascade) the Manna-Pnueli
class ladder is a CLEAN SWEEP — every case equiv=True. The open front is no
longer fidelity — it is output representation and verification at scale: the
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
  precondition checkable with `tests/kr/probe_reset_consistency.py`). Parse
  REVERSES coordinates: SgpDec is top-first (deeper levels read upper state),
  the operators peel index 0 first with the suffix as the self-contained
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

## Operators & current capabilities

The five reachability formulas are the literal constructions of paper Sec 4.2 /
construction-ref §7 (solid⁺ last-step with combined letters ⟨σ,T'⟩ over closure
configs + Leave-avoid/bad-predecessor conjuncts; Formula 5 lines (1)+(2)+(3),
swapped wsolid in line (2), no s==t guard; `reach_weak` the literal dual
¬reach(S,T,τ,B,β); `fin_c` per Lemma 7 with ι==C postponement). Case dispatches
compare FULL configs.

Construction is **hash-consed `spot.formula` DAGs end-to-end including the
output** (`reconstruct_ltl_paper_style` / `reconstruct_bls`; flattening opt-in
via `reconstruct_ltl_str` / size-gated `_str_f_gated` under
`KR_FLATTEN_TREE_LIMIT`), and **fully memoized** (`reach_strong` lru + the five
helpers keyed ⟨helper, casc, S, B, β, T, τ, level⟩; distinct-subproblem runaway
guard `KR_REACH_GUARD`, default 5M). Spot is used for hash-consing only — no
external calls on the hot path.

Layered on top (all default-ON unless noted; see `docs/HISTORY.md` for how each
landed, the soundness arguments, and the measurements):

- **Letter fusion** (`KR_FUSE_LETTERS`) — one summand per outcome class instead
  of per letter (Minato-minimized guard OR).
- **Own simplify + fold passes** (`aut2ltl/kr/simplify/`, `KR_SIMP_OWN`,
  `KR_SIMP_OWN_FOLD`, cap `KR_SIMP_OWN_LIMIT=2000`) — context pass, now-evaluation,
  partial factoring, unroll-inverse folds, initial-state opening, context-aware
  S1/S2 subsumption, arm-padding removal. Rules Spot lacks; per-node, amortized.
- **Per-conjunct Fin-reachability fold** (`KR_FOLD_FIN_REACH`) — keep `Fin(C∉M)`
  only for C reachable from the good set M in the config graph; decided before
  building the explosive `fin_c`.
- **Acceptance dispatch** (`aut2ltl/kr/acceptance_dispatch.py`), pre-checks at the
  head of `reconstruct_ltl_paper_style`, in chain order: `Acc(c)` bounded-fragment
  unroll (`KR_DISPATCH_ACC`, self-declining) → Büchi `⋁¬Fin` (`KR_DISPATCH_BUCHI`)
  → coBüchi `⋀Fin` (`KR_DISPATCH_COBUCHI`). Weak/looping `reconstruct_weak`
  (`KR_DISPATCH_WEAK`) is wired but **OFF** (correct, size regression). Direct
  hierarchy-class φ per Theorem 2 / §9.3; cover-aware α readers.

The portfolio front end and the sl gate live in `aut2ltl/portfolio/` (see that
package + STATUS "Validation"); the contract struct in `aut2ltl/contract.py`.

## Validation state

The ≥4-level dev guard is GONE (opt-in `KR_MAX_LEVELS` ceiling remains; the real
runaway protection is the distinct-subproblem guard). Depth ladder: `Xa` 3L →
`XXa` 4L → `XXXa` 5L → `X(a & Xa)` 5L.

- **MP ladder, portfolio path (default): clean sweep — every case equiv=True**
  (`logs/survey_gate_buchi2ltl_2026-06-14`, and the post-reorg re-runs
  `logs/survey_parch_step{5,6}_2026-06-14.txt`). The former residual
  (`F(a&Xb)`, `G(p->(qUr))`, `G(a->Xa)`, `GFa&GFb&GFc`, `G(a->Fb)`/`G(a|Fb)`,
  and the last wall `FGa|FGb`) all verify. A/B knobs: `KR_GATE_BUCHI2LTL=0`
  (pure kr decompose), `KR_DECOMPOSE=0` (monolithic).
- **Semantic grounding** (`trace_fin_semantics`, cover-aware GTs on the config
  semiautomaton): **zero contradictions** across every probed case at every
  depth; remaining sub-terms UNVERIFIED by size only. Every check Spot can
  complete is OK.
- Audit gate (`tests/kr/test_kr_r4_audit.py`): **CLEAN**.

## Open front: representation & verification at scale (not fidelity)

The construction is cheap; the flat form is the cost driver. Two consequences
remain live: (i) Spot translation hits the 32-acceptance-set tableau limit (one
set per distinct temporal subformula) on the biggest cases; (ii) the largest
flat strings still blow up. All test scripts carry built-in Spot budgets
(`KR_SPOT_EQUIV_TIMEOUT` / `KR_CHECK_TIMEOUT`, 10s) and report SPOT_TIMEOUT /
UNVERIFIED — never conflated with semantic failure. Full analysis and candidate
counter-measures: `dag_folding.md`; probed dead ends in `docs/HISTORY.md`.

**Size numbers are not pinned here** — they move with every fold change, so the
table that used to live in this section was stale. Measure on demand and diff:

- `tests/kr/survey_sizes.py` — size census (DAG / unfolded-tree / distinct-temporal
  nodes, sharing factor, build time) across the MP ladder on the shipped
  `reconstruct_decomposed` path. A/B knobs documented in its header.
- `tests/kr/compare_sizes.py OLD.txt NEW.txt` — per-case delta between two census
  logs; the distinct-temporal column (the 32-acc-cap driver) is the headline.
- `tests/kr/measure_formula_dag.py "<formula>"` — single-case DAG-vs-string blow-up
  (`--no-str` for the cases whose flat form is 100MB+).
- `tests/kr/logs/survey_sizes_*.txt` — persisted baselines for the diffs.

## Tooling for targeted work

All under `tests/kr/` (placed scripts only; subprocess isolation; small built-in
budgets — a blown budget is a finding, not a nuisance). One-shot probes are
committed, their finding recorded in `docs/HISTORY.md`, then deleted (git history
keeps them). `tests/kr/logs/` holds committed baseline size censuses for
before/after comparison of fold work.

- `survey_mp_cascade.py` — MP-class × depth ladder; construction and Spot-equiv
  phases in separate subprocesses with separate budgets (`KR_CONSTRUCT_TIMEOUT`
  30s / `KR_SPOT_EQUIV_TIMEOUT` 10s).
- `survey_sizes.py` — size census across the MP ladder on the decompose path
  (DAG/tree nodes, distinct temporals, sharing, build time; A/B knobs).
- `trace_fin_semantics.py` — per-config semantic grounding of fin_c sub-terms vs
  GTs on the config semiautomaton (cover-aware), witness words, per-check
  subprocess cap; verdicts OK/BAD/UNVERIFIED.
- `probe_reset_consistency.py` — soundness precondition: every combined letter
  acts identity-or-reset per level under both context conventions.
- `probe_sgpdec_api.g` — hand-run GAP ground truth for the SgpDec bridge calls.
- `probe_memo_stats.py` — memo profiler: distinct subproblems vs raw calls,
  helper-memo size, alarm + watchdog stack dump.
- `measure_formula_dag.py` — DAG vs string size of the assembled formula
  (`--no-str` for cases whose flat form is 100MB+).
- `probe_tail_anatomy.py` — per-level dissection of the helper memo.
- `probe_case_diff.py` — containment + witness for one full roundtrip (in-process
  build + fresh diff child via stdin).
- `ltl_diff.py` — containment direction + witness words.
- `test_kr_r4_audit.py` — structural checklist + drift grounding (gate for
  operator commits).
- `test_kr_zoom.py` / `test_kr_reconstruct.py` — single-case full trace /
  multi-case roundtrip with isolated equiv.
