# kr/ — Krohn-Rhodes / Holonomy Cascade Path

This subtree implements the algebraic translation from counter-free deterministic
ω-automata to LTL following:

> Udi Boker, Karoliina Lehtinen, Salomon Sickert.
> "On the Translation of Automata to Linear Temporal Logic". FoSSaCS 2022.

The approach is systematic and algebraic: **no pattern matching** on SCCs, terminal
components, or other shape-based rules (those live in the separate heuristic engine
under `buchi2ltl/`). Everything is driven by the reset cascade (holonomy decomposition
via SgpDec + GAP), the per-level Enter/Stay/Leave letter partitions, the configuration
mapping, and the inductive definition of the five reachability formulas + Fin(C) +
acceptance assembly.

## Documentation map (read in this order)

| doc | role |
|---|---|
| `paper/automata-to-ltl-construction.md` | **The construction reference.** Concise, self-contained: definitions, Table-1 semantics, the five formulas, Fin(C), per-acceptance assembly, worked example, pitfalls. Verified against the paper text. |
| `paper/Automata2LTL.txt` (+ `.pdf`) | **Ground truth.** pdftotext extraction; Section 4.2 + Table 1 + Formulas 3/4/5 are around lines 440–1040. Any formula-fidelity question is settled HERE, not in any summary. |
| `kr/algorithm.md` | Why this construction, scope/policy for kr/ (no pattern matching), complexity recap, mapping to modules. |
| `kr/STATUS.md` | Current state: what works, what fails, with the current minimal failing cases. |
| `kr/TODO.md` | Forward-looking work items only (history lives in git log). |
| `kr/dag_folding.md` | **Research direction (open):** why the construction explodes (measured), the DAG-vs-unfolding thesis, BDD-analogy gap analysis, candidate folding counter-measures, X-ladder benchmark protocol. |

Lesson learned (twice): LLM-generated paper summaries drift on case splits and guards.
A previous 1767-line reference doc introduced two classes of formula errors
(R4/Rws0 structure; a spurious `s ≠ t` guard on Formula 5) and was removed —
see git history. When in doubt, read the paper text.

## Pipeline

```
Spot automaton
→ normalize (in decompose_aut): deterministic complete minimized parity (min even),
  state-based acceptance ("sbacc" — required: the Muller condition is lifted over
  configurations, so the set of infinitely-visited states must determine acceptance)
→ extract generators (one per concrete letter in 2^|AP|)        kr/extract.py
→ self-contained GAP script (SgpDec HolonomyCascadeSemigroup;   kr/gap_bridge.py
  emits state lifts via AsHolonomyCoords, TRUE cascade transitions
  via lifted generators/OnCoordinates BFS-closed, and the cover map π
  via AsHolonomyPoint — holonomy coordinatization is a many-to-one
  cover, so config dynamics are never reconstructed through the lift;
  GAP RNG seeded for reproducible runs)
→ parse to Cascade (coordinates REVERSED: SgpDec top-first ↔    kr/gap/parse.py
  operators peel deepest-first with suffix context)
→ reachability formulas + Fin(C) + assembly                     kr/reachability*.py
```

Construction policy: hash-consed `spot.formula` DAGs end-to-end, full
memoization (reach + all five helper formulas), and **no external calls in
the hot path** — Spot is used for hash-consing only; `tl_simplifier` is
opt-in (`KR_SIMP_TREE_LIMIT`), and every Spot call in the test harness runs
under a small subprocess budget (a stall is reported, never waited on).

## Modules

- `cascade.py` — `Cascade` dataclass + `Config`: levels, state↔config (1-based coords),
  letter valuations, `move_config`, Enter/Stay/Leave helpers. Config-graph analysis
  (pruned config automaton, accepting configs, good Muller sets incl. the
  strongly-connected-subset enumeration) delegates to `config_graph.py`.
- `reachability_operators.py` — the five inductive reachability formulas
  (strong/weak, solid/dashed, >0 variants) with recursion to the level-0 base,
  memo + early simplify, `KR_TRACE=1` tracing; `fin_c` (Lemma 7).
- `reachability.py` — `reconstruct_ltl_paper_style`: good-Muller-set DNF assembly of
  ¬Fin/Fin conjunctions. `reconstruct_bls` is the public per-cascade entry (the
  Boker-Lehtinen-Sickert construction; thin wrapper over the assembly).
- `decompose_recombine.py` — **recommended top-level entry** `reconstruct_decomposed(aut)`:
  root decompose-and-recombine over the BLS construction. Splits the deterministic
  acceptance condition (AND by acceptance set / OR by strength), runs `reconstruct_bls`
  on each acceptance-trivial piece, recombines with ⋀/⋁. Orthogonal to the core;
  collapses the recurrence/mixed-strength census walls. See STATUS + TODO P1.
- `acceptance_dispatch.py` — **direct hierarchy-class φ per Theorem 2 / §9.3**,
  orthogonal to the Muller DNF. `reconstruct_buchi(casc)` = `⋁_{C∈α}¬Fin(C)`
  for Büchi cascades (else None → caller uses Muller); drops the `Fin(C∉G)` web.
  Büchi **WIRED** as a top-level pre-check in `reconstruct_ltl_paper_style`
  (gate `KR_DISPATCH_BUCHI`, default ON), so both the monolithic and decompose
  paths use it; α is cover-aware (`config_graph.buchi_accepting_configs`).
  `G(p->(qUr))` 84→14 temporals (survey equiv=True, totals −22%). coBüchi/
  looping/weak are TODO P1 (the active front — see STATUS + TODO P1).
- `gap_bridge.py`, `extract.py`, `gap/parse.py`, `bdd_utils.py` — decomposition
  pipeline and buddy-BDD stability.

## Usage

```python
from kr import reconstruct_decomposed
import spot

# Recommended top-level entry: automaton in, LTL formula DAG out.
aut = spot.formula("GFa & GFb").translate()
print(reconstruct_decomposed(aut))   # root decompose-and-recombine over BLS

# Lower-level, per-cascade: decompose then run the BLS construction directly.
from kr import decompose_aut, reconstruct_bls
casc = decompose_aut(spot.formula("Fa").translate())
print(casc)                          # summary + levels
print(reconstruct_bls(casc))         # Boker-Lehtinen-Sickert construction
```

## Dependencies

- `gap` on $PATH (GAP 4.12+) with SgpDec loadable (`LoadPackage("SgpDec")`).
- Run `./kr/install.sh` once (user-local under ~/.gap/pkg).

## Verification (kr/testing/)

All scripts run from the project root and use subprocess isolation (Spot/buddy can
segfault on state accumulation; rc 139 = segv). Placed scripts only — no /tmp,
no `python -c` one-liners.

- `test_kr_reconstruct.py` — isolated per-case decomp + reconstruct + Spot equiv
  (argv for specific formulas).
- `survey_mp_cascade.py` — Manna-Pnueli class × cascade depth survey; finds the
  smallest failing cases per class (drives targeted work, weakest class first).
- `trace_fin_semantics.py` — grounds every fin_c sub-term per config against
  ground-truth automata built from D's semiautomaton, with witness words.
- `ltl_diff.py` — directional language comparison (containment each way + witness
  word). Library + CLI.
- `test_kr_r4_audit.py` — R4/R5 structural checklist + semantic drift grounding;
  must report CLEAN before committing operator changes.
- `test_kr_zoom.py` — full trace for one formula (aut, cascade, Muller, KR_TRACE
  construction, equiv).
- `probe_reset_consistency.py` — soundness precondition of the paper formulas:
  every combined letter must act identity-or-reset per level (checked under
  both context conventions).
- `probe_memo_stats.py` — memo profiler (distinct subproblems vs raw calls)
  with a watchdog stack dump for stalls inside native calls.
- `probe_tail_anatomy.py` — per-level dissection of the helper memo (the tool
  behind the tails-drive-the-explosion finding).
- `probe_case_diff.py` — containment + witness for one full roundtrip when the
  flat formula cannot ride argv (in-process build, diff child via stdin).
- `measure_formula_dag.py` — DAG vs flat-string size of ONE assembled formula
  via the monolithic `reconstruct_ltl_paper_style` (`--no-str` for cases whose
  flat form is 100MB+).
- `survey_sizes.py` — size census across the MP ladder on the GOTO
  **decompose** path (`reconstruct_decomposed`): DAG/tree nodes, distinct
  temporals, sharing, build time. `KR_SIZE_PATH=monolithic` and
  `KR_FOLD_FIN_REACH=0` give A/B baselines. Construction-only, subprocess
  isolated, `KR_CONSTRUCT_TIMEOUT` budget.
- `probe_sgpdec_api.g` — hand-run GAP ground truth for the SgpDec bridge calls.
- `test_kr_basic.py` — normal-path smoke test (isolated per-case subprocesses).
- `logs/` — committed baseline size censuses (before/after reference for fold work).

One-shot probes (built to answer a single question) are committed, their
finding recorded in `kr/STATUS.md`, then deleted — git history keeps them.

## Notes

PoC/experimental. Limited to small |AP| (explicit 2^|AP| letters). Formula sizes
follow the paper bounds (large in the worst case). Sinks from Spot completion are
ordinary states. Generated GAP scripts are deterministic and self-contained.
