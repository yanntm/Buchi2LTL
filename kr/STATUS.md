# kr/ Current Status

**Goal of kr/**: Full general algebraic translation of counter-free deterministic ω-regular automata to LTL via Krohn-Rhodes holonomy reset-cascade decomposition (Boker–Lehtinen–Sickert, FoSSaCS 2022). *No pattern matching* on SCC structures, terminal components, fusion opportunities, or other shape-based rules from the original automaton. Everything is driven uniformly by the cascade components, per-level Stay/Leave/Enter partitions of letters, configuration mapping, and the recursive syntactic definition of the reachability formulas.

This path is separate from the heuristic reconstruction in `buchi2ltl/`.

## What is implemented

### Decomposition + Data (Paper Step 1 + part of 2)
- `decompose_aut` normalizes the input to a deterministic complete minimized parity automaton (min even) via Spot, extracts generators (explicit 2^|AP| letters), runs a self-contained GAP/SgpDec script (HolonomyCascadeSemigroup + AsCoords; special handling for 1-state), and parses the structured output.
- `Cascade` (cascade.py) is general: `num_levels`, `levels` (size/kind/structure), `state_to_config`/`config_to_state` (1-based), `letter_valuations`, `original_aut`, `generator_images`.
- Pure algebraic helpers (no original aut shape): `move_config`, `all_configs`, `top_of`/`sub_config`, `compute_stay_leave_from`, `compute_enters_to_from`, `build_config_transitions`/`build_configuration_automaton`, `accepting_configs` (Spot scc_info on non-rejecting SCCs with internal acc marks + t/f specials).
- GAP bridge, parser (focused in kr/gap/parse.py), extract (with bdd_utils for stable buddy var precompute), and install.sh are general. Synthetic path available.

### Reachability Operators + Paper Assembly (Paper Step 3 + 4/5/6 base)
- `reachability_operators.py`:
  - `letters_to_prop` / `make_guard`.
  - The implementation is the full inductive 5 formulas + base for all depths (no 1L special delegation or scalar helpers in the main path).
  - Full inductive 5 formulas (`reach_strong` primary = Formulas 1/3/5 with solid/dashed cases on source/bad/target, >0 disjunctions over Stay/Leave/Enter using lower-level recursion + sub-configs; landing and suffix early-outs for termination).
  - `reach_weak` (Formula 2) implemented as dual of strong per the paper (¬(S ~_T(¬τ) B(¬β))).
  - `fin_c` (Lemma 7) using the reach shorthands (ι ↝ C and C>0 ↝ C).
  - `simplify_ltl` (Spot), full (S,B,beta,T,tau,level) memo as unique table, early simplify on subformulas, PAPER_* counters, KR_TRACE=1 detailed traces (level, partitions, landing decisions).
- `reachability.py`:
  - `reconstruct_ltl_paper_style`: computes good M via Spot scc_info (non-rejecting SCCs), builds the top-level ϕ = ∨_M (∧_{C∈M} ¬Fin(C) ∧ ∧_{C∉M} Fin(C)).
  - `reconstruct_ltl_1level_buchi` (public entry) is a thin wrapper around the paper assembly (name kept for compat; practical >3L guard).
- `build_infinitely_often_accepting`, the old ad-hoc `_heuristic`, 1L-only fin_1/inf_1level, and associated special cases (G(stay) short-circuits, per-acc trapping F vs G(F)) have been removed.

Both 1L and multi use the generalized operators. TRACE + counters + memo keep construction bounded (O(exp) per paper).

## Current behavior (after parity min-even det complete norm)

- 1L (Fa, Ga, constants, some compounds after Spot norm) often recover simple equivalent LTL (Ga, Fa, true/false).
- 2L "a" currently yields "false" (or non-equivalent) via the assembly; Ga still good.
- 3L (Xa) and other 2L produce formulas (often large DNF-ish or degenerate) via the 5 formulas + Fin DNF; equiv frequently False.
- All core CASES in `kr/testing/` terminate with finite LTL and small call counts under the guards. Subproc isolation + bdd_utils = no segvs.
- `KR_TRACE=1` shows the exact inductive steps.

See `kr/testing/test_kr_*` output and the paper for expected size.

## Gaps (for full general + precision)

- Polish of the 5 formulas (exact conj/negations for leave/bad, entry logic, >0 cases per paper Table 1 / Sec 4.2) so more multi-level cases are correct and equivalent. (P0 focus on R4/Rws0 structural per reference notes: Line(2), no free-reach, case 4 precedence, R5 swap.)
- Trivial (size-1) level collapse (to reduce effective depth).
- Inside-construction guard simplification (beyond post-simp).
- Semantics validators in testing (execute cascade words vs. evaluate produced LTL).
- Hierarchy preservation and more paper examples / round-trips.
- Larger |AP| (current hard limit + explicit letters for tractability).
- Remove practical level guard (or make it size-based) once blowup is tamed.

**Recent P0 progress (targeted examples + commits per user):**
- Clean slate commit, then placed `kr/testing/test_kr_r4_audit.py` (R4 audit: drift grounding, 5-pt checklist, better canary G(p|Fq)).
- Commits after each item: audit script, then alignments (gt0_weak Line2+no-free-reach, weak solid case4+U-postpone, dashed line2+swap pattern).
- Audit runs (timeout 5 via placed script) now PASS all 5 checklist points + drift; canaries still targeted work needed.
- TODO.md + this STATUS kept up to date after each progress item. Working targeted (R4 cases + canaries) not full path.
- **Dealt with first arch item (leveraging spot.formula):** Core now uses native spot.formula builders internally (tested not worse via placed before commit: Fa/a EQUIV True).
- **Item 2+3 (Cascade + build_phi):** Added ref API (sigma, stay etc cl, Config) + build_phi(6 types). Placed tests confirm works + not worse (Fa/a True).

**Architectural elements from reference.md to adopt (prioritized, before more impl refinement):**
See TODO.md for details. Most important (high impact, low immediate risk, reduces future refactor):
1. Native `spot.formula` (DAG sharing, built-in .simplify()) + @lru_cache on R* fns (vs current strings + manual _reach_memo + post-simp). Reference emphasizes for triple-exp size. Adopt first via shim in arch script.
2. Refined Cascade (explicit combined-letter tuples, delta on (state,cl), first-class stay/enter/leave) + Config NamedTuple (vs current full-tuple move_config + top_of). Makes paper Rs0/Rc0 disjuncts direct.
3. Builders (And/Or/U/R/letter_to_ltl returning spot.formula) + full build_phi dispatch.
Start with 1+2 in targeted `test_kr_arch_adopt.py` (prototypes on R4 audit cases + canaries + Fa), then integrate. This is "architect first".

## Roadmap alignment (per algorithm.md)

- Step 1/2 (decomp + config paths): done, general.
- Step 3 (inductive reachability): 5 formulas + base + dual + recursion + utils done; polish remaining.
- Step 4/5/6 (Fin + acc encoding + top): `fin_c` + paper_style Muller DNF done; precision depends on formula polish + acc lift.
- See algorithm.md for exact definitions, complexity, and why this is the right systematic method.

`kr/algorithm.md` is the single canonical spec for what we are implementing. The original paper is at `paper/Automata2LTL.pdf`.

This file (STATUS) is intentionally short and factual about the *current* state of the code. Historical notes and "how we got here" have been removed.