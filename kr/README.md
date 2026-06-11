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
  ¬Fin/Fin conjunctions. `reconstruct_ltl_1level_buchi` is the public entry
  (name kept for compat; thin wrapper).
- `gap_bridge.py`, `extract.py`, `gap/parse.py`, `bdd_utils.py` — decomposition
  pipeline and buddy-BDD stability.

## Usage

```python
from kr import decompose_aut, reconstruct_ltl_1level_buchi
import spot

aut = spot.formula("Fa").translate()
casc = decompose_aut(aut)
print(casc)                 # summary + levels
print(reconstruct_ltl_1level_buchi(casc))
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
- `measure_formula_dag.py` — DAG vs flat-string size of the assembled formula
  (`--no-str` for cases whose flat form is 100MB+).
- `probe_sgpdec_api.g` — hand-run GAP ground truth for the SgpDec bridge calls.
- `test_kr_basic.py`, `test_kr_muller.py`, `test_kr_arch_adopt.py`,
  `diag_stability.py`, `probe_sbacc.py` — basics, Muller helpers, arch prototypes,
  stability, acceptance-marks probe.

## Notes

PoC/experimental. Limited to small |AP| (explicit 2^|AP| letters). Formula sizes
follow the paper bounds (large in the worst case). Sinks from Spot completion are
ordinary states. Generated GAP scripts are deterministic and self-contained.
