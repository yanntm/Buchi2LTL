# kr/ Current Status

**Note**: This document previously had a "before further coding" framing. The bulk of the original pre-refactor text has been retained below (lightly edited) as historical context. The "Progress after resume" section and refreshed "What is implemented" / "Gaps" sections reflect the post-refactor state (as of the 1-level clean reconstruction work and file splits for focus/stability).

**Goal of kr/**: Full general algebraic Büchi-to-LTL via Krohn-Rhodes holonomy cascade (Boker-Lehtinen-Sickert 2022), *without any pattern matching* on specific SCC structures (unlike the old buchi2ltl/ heuristics with f2/tN).

This is separate from the heuristic path. We want the systematic construction: decomp -> config paths -> inductive reachability K operators -> Fin/Inf -> acceptance encoding -> top LTL.

## What is implemented (current post-refactor state)

### Decomposition + Data (Paper Step 1 + part of 2)
- Full end-to-end: `decompose_aut(det_spot_aut)` (requires deterministic aut; use "Deterministic" in translate). Uses extract + generated GAP script (LoadPackage("SgpDec") + HolonomyCascadeSemigroup + AsCoords, adapted for SgpDec 1.x) + parse.
- `Cascade` dataclass is rich and general (see `cascade.py`):
  - num_levels, levels (size + kind/structure from SgpDec)
  - state_to_config / config_to_state (1-based coords)
  - generator_images (augmented with dead rejecting trap for incomplete auts — preserves language)
  - aps, letter_valuations (prop→bool dicts for every 2^|AP| letter — exactly for LTL guards)
  - original_aut ref
  - Methods (general, algebraic, no patterns): `move_config`, `all_configs`, `build_config_transitions`, `build_configuration_automaton`, `accepting_configs` (heuristic lift).
- Extraction completes incomplete auts with a dedicated dead rejecting trap (dead = n). Generators are total.
- Works on trivials, simples, and the motivating example (usable config auts even with dead trap).
- GAP bridge (`gap_bridge.py`), `install.sh`, `check_gap_available` are general. Synthetic path (`decompose_gens`) for testing without Spot.
- **File organization for focus/stability**: Parser moved to `kr/gap/parse.py` (small focused service); stability helpers in `bdd_utils.py` (precomputed buddy vars to avoid segfaults during extraction).

This part is solid and general (algebraic, no heuristic patterns on the automaton shape).

### Reachability Operators + Clean 1-level Reconstruction (Paper Step 3, base + clean top)
- Operators in `reachability_operators.py` (smaller focused file):
  - Helpers: `letters_to_prop`, `make_guard`.
  - 1-level base cases for reset levels: `one_level_reach_stay`, `one_level_reach_strong` (avoids B), `one_level_reach_weak`, `build_1level_reachability`.
  - General: take trans dict (from any config) + valuations + aps + τ tail. Build guarded U expressions from stay/change letters. No hard-coded patterns.
- High-level reconstruction (in `reachability.py`, now slim policy layer after splitting operators out):
  - `reconstruct_ltl_1level_buchi(casc)` — the **thin pure builder** (main path for 1-level). For num_levels != 1 it raises NotImplemented (use `_heuristic` for comparison/fallback on multi-level). Core logic: `build_infinitely_often_accepting()` which expresses "from the initial config, always eventually reach some accepting config" using `one_level_reach_strong(..., tau="true")`. Chooses `F(reach)` for absorbing acc sinks vs. `G(F(reach))` otherwise — decision made purely from the trans dict (no original_aut shape inspection, no dead/permanent/1-state/"q" filter special cases).
  - `reconstruct_ltl_1level_buchi_heuristic(casc)` — the old ad-hoc version (kept unchanged for A/B comparison during development; contains the structural ifs we wanted to move away from).
- Both versions + operators are exported in `kr/__init__.py`.
- 1-level cases (Fa, false, etc.) now go through the clean K-operator path and produce simple formulas equivalent to the original (verified via Spot `are_equivalent` in the `kr/testing/` harnesses).
- Fin_1level / inf_1level remain placeholders (will be expressed via K in future).

The 1-level path is now general/algebraic ("from init, G F (reach some acc via the operators)"), not ad-hoc. This was the main deliverable of the post-crash refactor work.

### Induction / Multi-level, Fin/Inf, Acceptance, Top Formula (Paper Steps 3–5)
- Core recursive 5-formula reachability implemented (in reachability_operators.py): base level-0, solid-stay (Formulas 3/4 with 4 S/B/T cases + >0 disj/conj over stay/leave using lower reach), dashed-change (5, using Enter + weak stay for prefix + force leave). reach_strong/weak entry points; simplify_ltl integrated. Cascade utils (sub_config, compute_stay_leave_from, compute_enters_to_from) added for partitions (pure via move_config).
- Multi now attempted in clean reconstruct/build_inf (no more hard NotImpl for >1); uses generalized reach_strong for any cascade depth (1-level delegates to old optimized for compat/nice output).
- Fin/Inf/acc assembly/Muller still missing (builder is still "inf often reach acc via K" generalized; safety G(stay) short for init-acc 1-level cases added + lift improved to not mark dead; for Ga now emits G(a) with equiv True). fin_c() sketch (Lemma 7 using reach) added as starting point for step 7.
- The 1-level foundation + new inductive ops provide the base; next: polish conj/negations in >0, Fin per Lemma7, full lift+assembly, semantics unit tests vs cascade runs.

### Testing / Examples / Other
- Full verification harnesses live in `kr/testing/` (see `kr/testing/README.md`):
  - `test_kr_reconstruct.py` — compares clean vs heuristic on curated cases (constants, 1-level, multi-level); uses subprocess isolation per case for stability; reports equiv where possible.
  - `diag_stability.py` — repeated isolated decomp on historically crashy cases (Xa, etc.).
- Demos: `examples/spot_det.py`, `examples/synthetic.py` (extract + config aut + 1-level reach starters).
- Generated .gap scripts in `examples/generated/`.
- No dependence on old f2/tN patterns.
- Still limited to small |AP| (explicit 2^|AP| letters).
- Cascade data from SgpDec is faithfully represented.
- Stability: bdd_utils precompute + isolation eliminated sporadic segfaults during extraction (verified repeatedly).

## Historical note (pre-1-level clean refactor)
(The following text is retained from the original "before further coding" version for context.)

### Top-level Reconstruction (old ad-hoc state)
- The original `reconstruct_ltl_1level_buchi(casc)` contained significant ad-hoc structural logic (early returns using original_aut, special handling for 1-state/dead/permanent sinks, has_bad_self checks, special "q" filters for until cases, fallbacks to guarded U + GF).
- It produced correct equivalent formulas for many trivials/simples via special paths, but for the motivating G(p→(q U r)) (then 1-level) it was not equivalent.
- This was exactly the "pattern matching on structure" we wanted to avoid. It served as a prototype while building the operators.

(The rest of the historical gaps around induction etc. have been incorporated into the current "Gaps" section below.)

## Gaps for the full general approach (updated)
- **Multi-level induction** (core remaining piece): Basic recursive implementation of the 5 reachability formulas added (reach_strong/weak + solid stay 3/4 with 4 cases + >0 + dashed 5 using Enter/Leave + sub recursion on projected lower configs via new Cascade sub_config / compute_stay_leave/enter_from). Uses level-0 base U + delegation for top 1-level. Still approximate in conj/negations for leave/bad and entry logic; produces degenerate (0/1/true) or partial formulas on some multi (e.g. F(0), G(F(1))). Needs polish + semantics validation.
- Fin/Inf: Still placeholders (1level); generalized reach now available to implement Lemma 7 Fin(C) := ¬(ι ↝ C) ∨ ι ↝ C ( ¬(C>0 ↝ C) ).
- Acceptance encoding + full top not general (still "inf often via reach" builder, now multi-capable but not using Fin/Muller disj).
- Acc lift heuristic (still); better marking needed for precise.
- Safety vs recurrence framing: Partial fix in build_inf (G(stay_g) short-circuit when init acc + constrained stay letters; prefers safety G for Ga family). Triggered for some; more cases (closed acc sets, attach G(stay) to after-tau) remain. "a"/"Ga" still not always ideal post-decomp (dead trap).
- Guard simplification: Called via simplify_ltl (Spot) at end of reach_strong etc. Reduces some; make_guard still emits long DNFs in >0 disjs (future: simp inside make too).
- Trivial levels / cascade utils: Added top_of/sub_config/compute_*_from (prereq for partitions). Trivial size-1 levels not yet collapsed (can project to reduce effective levels for clean path).
- Still small |AP|.

The decomp/config part and the clean 1-level reconstruction are in good general shape. The LTL construction is now at "1-level operators + thin pure K-based top for 1-level" (no more ad-hoc in the main 1-level path).

## On the roadmap steps (updated)
- Step 1 (decomp semi-aut to cascade): Covered, general (with stability improvements via bdd_utils and focused parser in kr/gap/).
- Represent runs as config paths (step 2): Covered (config aut + build_* methods).
- Define reachability inductively (step 3): Base 1-level K operators exist and are general (in the smaller `reachability_operators.py`). The thin clean `reconstruct_ltl_1level_buchi` + `build_infinitely_often_accepting` is the pure builder on top of them. **Ready for the induction** — implement the recursive multi-level versions of the operators per the paper (using sub-reach on lower levels for Stay/Leave/Enter cases). This remains the core missing piece for "full general".
- Fin/Inf (step 4), acceptance (step 5): Not yet.

We now have the clean 1-level foundation (operators + thin builder using K only) that the induction can build on. The operators give us the reusable base to recurse.

See `kr/testing/` for the harnesses that compare clean vs heuristic and validate stability/equivalence on curated cases.

### Historical progress note (post-crash refactor)
- Old ad-hoc body isolated as `reconstruct_ltl_1level_buchi_heuristic`.
- New thin `reconstruct_ltl_1level_buchi` + `build_infinitely_often_accepting` (uses `one_level_reach_strong` on init→acc with tau=true; F vs G F chosen from trans dict for absorbing accs).
- Split for smaller focused files: `reachability_operators.py`, `bdd_utils.py` (stability), `gap/parse.py`.
- Stability: precomputed buddy var map once before the per-letter loop; Xa and other cases now reliable in repeated isolated runs.
- Pure 1-level cases (Fa, false, ...): clean path taken; "false" and Fa give correct equivalent LTL via the pure K path (no structural ifs).
- Both versions + operators exported; heuristic available for comparison.
- (Further tuning of top-level obligations, guard simplification, and multi-level induction remain.)

## The Paper Gist (for reference, no pattern matching)
See the canonical single description in `kr/algorithm.md` (fused best-of-both from detailed algorithmic steps and explanatory motivation). It is the authoritative reference for the systematic algebraic method we are implementing in kr/ (no pattern matching). The original paper is now tracked in the repo at `paper/Automata2LTL.pdf`.
- Krohn-Rhodes reset cascade as the intermediate representation (exactly what our `Cascade` + holonomy via SgpDec already produces).
- The 5 reachability formulas defined by induction on cascade levels (with Stay/Leave/Enter cases, strong/weak, >0 variants).
- Inductive proof of semantics w.r.t. cascade runs + size bounds (linear depth per level, singly-exp length per level).
- Combining with holonomy decomposition → double-exp depth / triple-exp length overall.
- Preservation of syntactic future hierarchy / acceptance classes.
- Explicit contrast to ad-hoc heuristics: everything is driven uniformly by the algebraic cascade structure and the Stay/Leave partitions of letters; no inspection of original SCC shapes, terminal components, fusion opportunities, etc.

This file is the authoritative "what we are trying to implement" document for the kr/ folder. The current 1-level operators and `build_infinitely_often_accepting` are the base case / specialization of the reachability formulas (Lemma 7 Fin/Inf via reachability is already sketched there).

Next implementation steps remain as listed in the gaps section above (generalize to the full 5 formulas + induction on levels, implement Fin(C), lift acceptance, add guard simplification, handle trivial levels, etc.).

