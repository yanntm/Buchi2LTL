# aut2ltl/kr — Krohn-Rhodes / Holonomy Cascade Path

This subtree implements the algebraic translation from counter-free deterministic
ω-automata to LTL following:

> Udi Boker, Karoliina Lehtinen, Salomon Sickert.
> "On the Translation of Automata to Linear Temporal Logic". FoSSaCS 2022.

The approach is systematic and algebraic: **no pattern matching** on SCCs, terminal
components, or other shape-based rules. Everything is driven by the reset cascade
(holonomy decomposition via SgpDec + GAP), the per-level Enter/Stay/Leave letter
partitions, the configuration mapping, and the inductive definition of the five
reachability formulas + Fin(C) + acceptance assembly.

The shape-based heuristic engine `aut2ltl/sl/` (backward labeling) is no longer kept
strictly apart: it is wired into the decompose dispatcher as a **sound pre-filter
gate** through the single seam `aut2ltl/portfolio/heuristic_gate.py` (default ON). Its core, `sl`
(self-loop / semi-linear backward labeling), is an EXACT state-elimination translation
on the very-weak (1-weak) fragment — automata whose only cycles are self-loops — and
DECLINES (`UNSUPPORTED`) on anything with a genuine multi-state cycle, so it is sound
by construction; its f2/t2 layer is a separate verify-before-use guess-and-check. The
gate tries it per node (raw input + each split piece) and falls through to the cascade
when it declines — decomposition exposes very-weak pieces, the algebraic cascade
carries the multi-cyclic core. **Authoritative sl/soundness description:
`aut2ltl/portfolio/heuristic_gate.py` module docstring** (read it before re-reasoning about sl). As
the FoSSaCS'22 BLS construction has, to our knowledge, no prior practical
implementation, this subtree is the first.

## Documentation map (read in this order)

| doc | role |
|---|---|
| `paper/automata-to-ltl-construction.md` | **The construction reference.** Concise, self-contained: definitions, Table-1 semantics, the five formulas, Fin(C), per-acceptance assembly, worked example, pitfalls. Verified against the paper text. |
| `paper/Automata2LTL.txt` (+ `.pdf`) | **Ground truth.** pdftotext extraction; Section 4.2 + Table 1 + Formulas 3/4/5 are around lines 440–1040. Any formula-fidelity question is settled HERE, not in any summary. |
| `algorithm.md` | Why this construction, scope/policy for kr/ (no pattern matching), complexity recap, mapping to modules. |
| `STATUS.md` | Current state: what works, what fails, with the current minimal failing cases. |
| `TODO.md` | Forward-looking work items only (history lives in git log). |
| `dag_folding.md` | **Research direction (open):** why the construction explodes (measured), the DAG-vs-unfolding thesis, BDD-analogy gap analysis, candidate folding counter-measures, X-ladder benchmark protocol. |

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
→ extract generators (one per concrete letter in 2^|AP|)        extract.py
→ self-contained GAP script (SgpDec HolonomyCascadeSemigroup;   gap_bridge.py
  emits state lifts via AsHolonomyCoords, TRUE cascade transitions
  via lifted generators/OnCoordinates BFS-closed, and the cover map π
  via AsHolonomyPoint — holonomy coordinatization is a many-to-one
  cover, so config dynamics are never reconstructed through the lift;
  GAP RNG seeded for reproducible runs)
→ parse to Cascade (coordinates REVERSED: SgpDec top-first ↔    gap/parse.py
  operators peel deepest-first with suffix context)
→ reachability formulas + Fin(C) + assembly                     reachability*.py
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
  Büchi (`⋁¬Fin`) and coBüchi (`⋀Fin`, persistence) both **WIRED** as top-level
  pre-checks in `reconstruct_ltl_paper_style` (gates `KR_DISPATCH_BUCHI` /
  `KR_DISPATCH_COBUCHI`, default ON), so both the monolithic and decompose paths
  use them; α readers are cover-aware (`config_graph.buchi_accepting_configs` /
  `cobuchi_finite_configs`). The coBüchi gate recovers the natural acceptance via
  `postprocess(.,"generic")` (the parity step hides `Fin(0)` as `Inf(0)|Fin(1)`).
  `G(p->(qUr))` 84→14 temporals; persistence totals −40%. The weak/looping
  (Δ₁/Σ₁/Π₁) form `reconstruct_weak` (pure `reach_to`, no Fin) is also wired but
  **OFF by default** (`KR_DISPATCH_WEAK`): correct, but a size regression — weak
  languages are already smaller under Büchi/coBüchi and the residual is
  reach-driven. The config-indexed **`Acc(c)`** dispatch `reconstruct_acc`
  (`KR_DISPATCH_ACC`, default ON, first in the chain) handles the BOUNDED fragment
  by bounded unroll (no reach/Fin, self-declines on recurrent configs → BLS) and
  **cracks the `X(a&Xa)` reach wall** (UNVERIFIED 5.1×10⁸ → literal, equiv=True).
  See STATUS + TODO P1.
- `heuristic_gate.py` — the SINGLE seam to `aut2ltl/sl/`. `try_heuristic_gate(aut)`
  converts an arbitrary HOA to a TGBA (Spot, language-preserving), runs buchi2ltl's
  backward labeling (the exact `sl` core + the verify-before-use f2/t2 layer),
  simplifies the result through `_simp_f`, and returns the formula DAG or None.
  Tried per node by `decompose_recombine` (default ON, `KR_GATE_BUCHI2LTL`); opt-in
  `KR_GATE_VERIFY` audit. Cracks the `FGa|FGb` wall (2779→3 temporals); MP survey is
  a clean sweep. Soundness rationale + sl description live in this module's docstring.
- `gap_bridge.py`, `extract.py`, `gap/parse.py`, `bdd_utils.py` — decomposition
  pipeline and buddy-BDD stability.

## Usage

```python
from aut2ltl.portfolio import reconstruct_decomposed   # the portfolio front end
import spot

# Recommended top-level entry: automaton in, ReconResult out (.formula DAG +
# .technique). The portfolio composes the kr engine with the sl gate.
aut = spot.formula("GFa & GFb").translate()
print(reconstruct_decomposed(aut).formula)   # root decompose-and-recombine over BLS

# Lower-level, per-cascade: the PURE kr engine, decompose then run BLS directly.
from aut2ltl.kr import decompose_aut, reconstruct_bls
casc = decompose_aut(spot.formula("Fa").translate())
print(casc)                          # summary + levels
print(reconstruct_bls(casc))         # Boker-Lehtinen-Sickert construction
```

## Dependencies

- `gap` on $PATH (GAP 4.12+) with SgpDec loadable (`LoadPackage("SgpDec")`).
- Run `aut2ltl/kr/install.sh` once (user-local under ~/.gap/pkg).

## Verification (tests/kr/)

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
finding recorded in `STATUS.md`, then deleted — git history keeps them.

## Notes

PoC/experimental. Limited to small |AP| (explicit 2^|AP| letters). Formula sizes
follow the paper bounds (large in the worst case). Sinks from Spot completion are
ordinary states. Generated GAP scripts are deterministic and self-contained.
