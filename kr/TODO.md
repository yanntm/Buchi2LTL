# KR / Automata-to-LTL Implementation TODO

Based on `kr/automata_to_LTL_reference.md` (the LLM-generated paper summary + detailed call-to-action / implementation guide with formal defs, 5-formula pseudocode, 19 practical steps, toolchain, examples, limits, and Spot/GAP sketches) cross-referenced against the current kr/ codebase (as of latest state in STATUS.md, algorithm*.md, source in cascade.py/reachability*.py/gap_bridge.py + testing/, and recent patches for paper fidelity on cases like Fa).

**Two sections only.** Items are specific, actionable, and traceable to the reference or gaps in current code. Some overlap with old algorithm.md "missing pieces" (which are partially outdated vs. STATUS).

Prioritization is suggestive (based on ref's emphasis on "exact" defs for correctness + "critical optimizations" like memo/simplify/prune for feasibility); final order to be discussed/approved.

---

## DONE (already present / substantially implemented in the code base)

- Full formal background coverage in project docs (LTL syntax/semantics/hierarchy, automata defs, acceptance conditions + hierarchy correspondence, cascade/wreath product defs, Enter/Stay/Leave partitions, holonomy/KR decomposition Prop 6, lifting Props 7/8, shorthands ι~~C and C>0~~>C, Fin(C) Lemma 7, top-level assembly per Theorem 2 for Muller/Büchi/coBüchi/weak/looping cases, complexity bounds). See `kr/algorithm.md`, `kr/algorithm_2.md`, now `kr/automata_to_LTL_reference.md` (added), and paper/ dir. (Ref Part I is now the detailed reference.)
- Decomposition pipeline (ref Steps 1-4 + toolchain): Spot `translate` + norm to det complete min-even parity DPA (authoritative D), generator extraction (2^|AP| explicit letters via valuations), self-contained GAP/SgpDec Holonomy (via `decompose_aut` + gap_bridge + kr/gap/parse.py), Cascade dataclass with levels, state↔config h (1-based tuples), letter_valuations, move_config, top_of/sub_config, compute_stay_leave_from / compute_enters_to_from (using full configs + top), build_config_transitions / pruned config aut (with buddy.bddtrue fix + acc lift), reachable_configs (BFS), accepting_configs (via scc_info or self-loop proxy), build_pruned_config_aut + compute_good_muller_sets (prefers config SCCs + basin fallback). bdd_utils for buddy var stability. install.sh. (Ref sections 10-13, 15, 18; current code matches most sketches, though uses generator_images + state lifting rather than explicit per-level delta on combined letters.)
- Guard / letter helpers (ref Step 6): letters_to_prop / make_guard; letter_to_ltl equivalent in spirit.
- Inductive 5 reachability formulas + base (ref Sec 5 + Step 6): reach_strong (F1), reach_weak (F2 as dual), _solid_stay_strong + _stay_gt0_strong (F3 + >0), _solid_stay_weak + _stay_gt0_weak (F4), _dashed_change_strong (F5), with source/bad/target cases (4-way), s_val != t_val early false for solid, suffix match early (conditioned on trivial tau=true post-patches), landing complete in gt0, leave conjs + bad-landing forbids, level cursor on full tuples (preserves higher context), recursion to base level==n as (¬β)Uτ or G(τ | !β). Recent patches: U form in solid target for complex tau (to support Fin last-visit postponement), base (¬β)U core inject in dashed enter when lower_T empty (for 1L "F" cases), no-early for non-true tau in reach_strong, no outer force in dashed. KR_TRACE, PAPER_* counters, simplify_ltl (Spot) on subs + results, manual _reach_memo (S,B,beta,T,tau,level,id) as unique table. (Ref 5.1-5.3, 15; current is string-based approximation of the Rs0/R3/R5 structure + 4 cases; has been iteratively aligned to paper derivations for Fa/"a".)
- Fin(C) + shorthands (ref Sec 6 + Step 7): fin_c per Lemma 7 using reach + _uncond_reach_strict (C>0), updated to use direct paper "reach with tau=¬(C>0~>C)" (no_return_psi + r_with) instead of post-hoc G/ & approx (post-patches). reach shorthands in reachability.py. (Ref 6.1-6.2, 16.)
- Top-level assembly + acc lifting (ref Sec 6.3 + Steps 14/16): reconstruct_ltl_paper_style + _compute_good_muller_sets (Muller DNF ∨_M (∧ ¬Fin for M, ∧ Fin for notM); good M from pruned config aut SCCs (non-rejecting) + basin fallbacks, not blind powerset). Special handling in code for t/f/true/false/weak/looping (via original_aut acc or scc). reconstruct_ltl_1level_buchi thin wrapper (compat name). (Ref 6.3 cases 1-6, 14, 16; current covers Muller primary + specials; full build_phi sketch in ref is more exhaustive.)
- Practical enablers from ref "Critical optimizations" (Step 18): aggressive early simplify + normalize (0/1, X(true) etc via Spot), memo (unique table), counters to detect explosion, prune to reachable (in cascade + good_ms), dead config avoidance in practice (BFS), trivial early-outs (solid false on top change, suffix, etc.), KR_TRACE for step-by-step, 5s timeout discipline + placed scripts only in testing/ (no /tmp long -c), subproc isolation in tests (test_kr_reconstruct etc), bdd_utils precompute. (Ref 18 + testing/README.)
- Testing / verification skeleton (ref Step 17): kr/testing/test_kr_basic.py, test_kr_reconstruct.py (isolated per-case + Spot equiv), test_kr_zoom.py (trace aut/cascade/muller/recon/equiv for formula arg), diag_stability.py, test_kr_muller.py. Roundtrip checks on CASES (true/false/a/Fa/Ga/Xa/...). Zoom shows aut, norm D, cascade, reachables, acc, good_ms, pruned config SCCs, KR_TRACE construction, recovered + equiv. (Ref 17, 19 end-to-end sketch.)
- Special cases / hierarchy alignment: 1L often yields simple (Fa/Ga/true) via the general path (post L1-deletion); some weak/looping handled in assembly or fin. (Ref 3.5, 6.3 cases 4-6, 17.)
- Docs + discipline: kr/README.md, STATUS.md (factual current state, no history stories), algorithm*.md (spec), reference.md (new detailed ref + pseudocode), no commits without say-so, per-file diffs + reads + tests. (Ref 9 toolchain, 18.)
- Small examples work (Fa, a, Ga, G(p) spirit via 1L looping); counters small under guards; no segvs.

Many "missing pieces" listed in older algorithm.md (e.g. full 5 formulas, Fin, assembly, general path for all depths, no L1 special) are now DONE per STATUS + recent patches. Ref's pseudocode (R1/R3/R5 with exact Rs0 conjs, 4 cases, R5 3 lines) is the precise target the current generalized operators aim to match (string form).

**Recent P0 progress (R4/Rws structural, per user direction to use targeted examples + commits on each item):**
- Created + committed placed `kr/testing/test_kr_r4_audit.py` (implements Path A semantic grounding/drift-forever, Path C exact 5-point checklist on _stay_gt0_weak/_solid_stay_weak/_dashed, Path D better canary like G(p|F q), runs under timeout 5).
- Committed clean-slate first (as directed).
- Partial alignments committed: _stay_gt0_weak now has explicit Line(2) stay-forever + omits free-reach (matches corrected Rws0); _solid_stay_weak case 4 uses weak form + U on target for postpone; _dashed_change_strong has line2 + swapped-role weak call pattern for R5(2).
- Audit re-runs (via placed script) now show all 5 checklist points PASS; drift PASS; canaries still need work (targeted, not full path).
- Kept TODO/STATUS up to date after each item.
- **2025 session start (R4 audit stabilization per user):** Began with audit tool (no core changes yet). Improved placed `test_kr_r4_audit.py` (one increment): precise _get_func_body extraction for checklist points (no global-string false positives), semantic Spot check (G(drift) & !phi lang empty?) for Path A instead of crude heuristic, better tau choice + postpone logic that accepts vacuous "true" or U-forms without false-gating overall. Re-ran under timeout 5: now 5pts PASS + semantic drift PASS + behavioral U example, overall "CLEAN FOR PROCEED". Canary still FAIL (correct signal). One commit per file discipline + todos/status maintained before each commit. See STATUS + the audit run in next items. This stabilizes the diagnostic before editing the hard Rws0/R4 case logic in operators.
- **Item 2+3 progress (Cascade API + build_phi):** Added ref API (sigma, stay/enter/leave cl tuples, Config, make_config) to cascade.py (compat). Added build_phi dispatch (6 types) to reachability.py. Updated+ran placed arch_adopt to test: API works, build_phi ok, Fa/a equiv True (not worse per tests before commit). See arch script output.
- **Dealt with first arch item (leveraging spot.formula, per user):** Refactored reachability_operators.py to use native spot.formula builders (_tt/_And/_Or/_U/_X/_Not/_letters_to_f/_to_f/_str_f) + formula objects for internal trees/keys in reach_*/_solid_*/_stay_gt0_* (enables sharing). Public str compat. Tested via placed scripts (r4_audit, arch_adopt, basic Fa/a, zoom Fa/a/G(p|F q)) BEFORE commit: Fa/a EQUIV True (same/not worse), no crashes, R4 functional, canary runs. Committed only after (9782f3a).
- **Tried lru on R*:** Added _casc_by_id registry (_register/_get/_clear) + @lru_cache(maxsize=None) on _lru_reach_strong(cid, S, B, beta_f, T, tau_f, level) [beta/tau now spot.formula hashable]. reach_strong delegates (after _to_f + register). Cache cleared in reconstruct. Confirmed hits in placed arch_adopt (e.g. hits=6 on Fa run). All targeted tests (basic/zoom Fa/a EQUIV True same, r4_audit drift PASS, arch) not worse. Docs updated. Committed after.
- Updated TODO/STATUS after item.

**Architectural adoption from reference (high priority before more impl refinement):**
See STATUS.md + `kr/testing/test_kr_arch_adopt.py`. Most important (adopted #1):
- Native `spot.formula` + builders + lru on R* (DAG sharing; this item).
- Refined Cascade + Config.
- Full build_phi etc.
Next: complete lru integration (more helpers), then Cascade.

---

## TODO (items to consider adopting / gaps vs. the reference call-to-action)

**Refined prioritization (post paper pp.11-12 analysis):** The reference's call-to-action (especially the exact R4/Rws0 + R5 line(2) details) makes clear that certain "formula fidelity" items are *semantic correctness bugs*, not polish. P0 items below must be resolved (via the audit paths in the patched reference.md) before optimizations or extra test volume. The reordering below directly incorporates the analysis: R4/Rws structural issues (3 precise errors + swap requirement + case-4 precedence) are elevated to their own top-level P0 cluster with the exact 5-point checklist. "Weak formulas" is no longer a vague sibling bullet.

Many items remain "refine/align" (current generalized ops are a working approximation that has been patched for Fa etc., but must be validated against the literal paper expansions for Rws0 etc.). Cross-ref to ref sections/steps + the new "Audit & Validation Notes for R4..." subsection now in `kr/automata_to_LTL_reference.md`.

### P0 (correctness bugs — fix / audit / validate first; blocks everything else)
- **R4 (Rws + Rws0) structural correctness (paper pp. 11-12; three precise errors + R5 downstream impact).** 
  - Rws0 line (2) "stay-forever" disjunct (the vacuous "drift in s forever with no Leave/bad-predecessor ever firing") must be present and OR-ed with line (1). (No Rs0 analogue.)
  - Rws0 line (1) must *omit* the unconditional "freely reach T'" conjunct that Rs0 has; the two Rw avoids make T' conditional on blocking events.
  - Bad-predecessor (and Leave) avoids inside Rws0 must use Rw (weak), not R.
  - Outer Rws case 4 (S=B ∧ S=T) must be exactly `(Rws0 ∨ τ) ∧ ¬β` (¬β is global side-condition; immediate τ does not override). The strong form `(Rws0 ∧ ¬β) ∨ τ` is wrong for weak.
  - R5 line (2) must call the weak formula with *swapped roles* (original (T,t,τ) as the "bad" role; original (B,b,β) as the "target" role). Non-swapped calls are incorrect. (Rws, not R, because avoidance is conditional.)
  - Current code (level-cursor _solid/_gt0/_dashed + recent U patches) approximates but must be audited against the literal expansions. Add ref's Rs0/Rws0/R3_pos etc. (or equivalent) as internal helpers or exhaustive comments. Use the 5-point checklist from the reference.md "Audit & Validation Notes" section.
  - (Ref Sec 5.2, 5.3 dep graph, R5 formal, and the dedicated corrections subsection now patched into reference.md.)
- **Better canary tests for R4 (Fa is insufficient).** 1L looping-coBüchi cases like Fa/Ga often bypass R4 (shortcuts to R1). Use Büchi/coBüchi cases whose output is in Π₂/Σ₂ and that exercise Fin(C) (which uses reach-with-tau forms depending on inner Rws for last-visit postponement), e.g. `G(p ∨ F q)`. Roundtrip (Spot equiv) failure after R4 work is a strong signal. Add semantic grounding / duality tests per the "Paths to fix" in reference.md (e.g. pure-stay words on a 1L reset cascade where S=T but B differs at top; check "drift forever" satisfies Rws).
- Full support for parameterized tau=ψ in "last visit" (ι ~ C (ψ)) inside Fin/reach, with proper postponement via the corrected Rws0 (for transients init==C). Validate the Fin(N) = Fa case for 1L Fa (and equivalents) using the new canaries.

### P1 (correctness for coverage + full acc paths)
- Ensure 4-case handling + >0 variants + exact Enter/Leave/Stay usage across *all five* (incl. the now-corrected R4 weak differences and R5 line 2/3). Current has source_is_target/source_is_bad logic + landing/suffix early-outs, but audit for the weak specifics and any suffix vs. single-val inconsistencies (e.g. in _solid_stay_weak). (Ref 5.1 Table 1 semantics, 5.2.)
- Complete build_phi / acc-type dispatch for all 6 cases (looping-buchi/cobuchi, buchi/cobuchi via negate, muller DNF, weak H/H') using the exact sketches (incl. looping sink preimages, weak reachable-from-G but not-in-G). Current has muller primary + specials in reconstruct/accepting_configs/fin; extend + use for hierarchy preservation. (Ref 6.3, 16, 17.)
- Muller lift: ensure full (powerset of preimage whose h-image exactly == M) + SCC-based pruning on the *cascade* graph (or on the existing pruned config aut) as feasibility gate for n>2. Current uses scc_info on pruned config aut + basins (good foundation); add the exact lift + dedup + warning. (Ref 14, 18.)
- Base + level 0 exact (plain U or G form); recursion strictly decreasing level. (Ref 5.1, 5.2.)
- Weak formulas (R2/Rw/R4/Rws) *full and used where paper requires* (R5 line 2 explicitly uses Rws with the swap; weak paths for safety classes / Fin inner logic). Current _weak exists but main path + fin lean on strong; ensure the corrected Rws is exercised. (Ref 5.2, 5.3 deps, R5 formal.)

### P2 (feasibility enablers — after P0/P1 validated)
- Switch (or dual-track) to native Spot formula objects (DAG via spot.formula.And/Or/U/R/X/Not + lru_cache keyed on normalized forms) instead of (or in addition to) string building + post-simp. Current memo + simplify_ltl works for small n; ref stresses DAG sharing for the triple-exp bound. Add letter_to_ltl etc. builders. (Ref 15, 17, 18 #1-3.)
- Simplify *at every construction step* (after each And/Or/U/R in the R*/Fin builders), not just final or in gt0/assembly. (Ref 18 #3, 17.)
- More pruning: precompute reachable from ι and only ever build formulas/caches for them; trivial early-outs (Enter(t)==∅ ⇒ false; Stay(s)==∅ ⇒ tau/false per the 4 cases); detect/collapse size-1 levels to reduce effective depth. (Current has BFS reachable + some early-outs; make systematic.) (Ref 18 #4-5, 20.)
- Memo key robustness (hashes or Spot-normalized forms for beta/tau; current uses simp'ed strings — sufficient for now but improve). (Ref 18 #1.)
- Hierarchy preservation + output class tagging (Σ/Π/Δ_i per Lemma 5) on produced formulas. (Ref 5, 6.2.)
- Larger |AP| support (on-demand generation or BDD-based guards instead of full explicit 2^k). Current noted hard limit. (Ref 18 table.)
- Remove/make dynamic the >3L guard in reconstruct_ltl_... (size/depth-based) once P0/P1 are solid. (Ref 18.)

### P3 (testing + completeness + docs)
- Semantics validator: sample words from the (normalized) aut or by walking the cascade configs, check aut acceptance ⇔ φ truth value (via Spot translate or direct LTL eval on the word). Add to kr/testing/ (use the "Fa regression as canary" idea but with the better P0 canaries). (Ref 17 verify, 19 end-to-end.)
- Hierarchy + roundtrip on more paper examples (full G(p), unary cases per Sec 7, weak/looping, Rabin/Muller beyond current 1L/2L). Extend CASES in test_kr_reconstruct + zoom traces. (Ref 8 worked ex, 19, 7.)
- Full end-to-end script/example (matching ref Step 19 sketch) + verify. (Ref 19.)
- Expand tests: more multi-L roundtrips, stability/repeats, size/depth metrics vs paper bounds (O(2^{2^n}) depth, 2^{2^{O(2^n)}} length), per-acc-type specific. (Ref 18, testing/.)
- Finite-word variant (weak-next / R in appropriate places per remark). (Ref 7 optional.)
- Past operators / elementary LTL+past → pure-future (stretch, per notes). (Ref 7.)
- Update STATUS.md + algorithm.md + README.md to be current (old algorithm.md still lists some "missing" items that are DONE; reference.md is now the detailed + corrected spec). Remove stale claims. (Ongoing doc hygiene per prior rules.)
- GAP/Python interface options (subprocess is solid; optional SageMath bindings sketch). (Ref 18.)
- Spot shortcuts for pure safety/co-safety (bypass full Muller/Fin for looping-buchi/cobuchi cases to stay in Σ₁/Π₁). (Ref 17, 18 #6.)
- Counter-free explicit verification (GAP IsAperiodic / maximal subgroups trivial) — for external HOA inputs (LTL-derived are guaranteed). (Ref 12, 18.)
- Lift for Rabin pairs if targeting beyond current Muller focus. (Ref 6.3, Prop 7.)

### Stretch / later (ref notes, complexity, 7)
- Unary alphabet tight bounds demo + contrast with LTL→aut.
- No known lower bounds above linear (research note; close the gap?).
- Full complexity measurement on examples (depth/length vs. paper O(...) bounds).
- Integration hooks with main buchi2ltl/ (kr/ as exact algebraic backend for small counter-free cases?).
- Performance (cross-run caching, etc.).
- (The reference's "Part I" formal coverage is now patched for the R4 gaps noted in the query.)

---

**Suggested next (non-code) steps after this doc adaptation (see report below):**
- (You approve the refined TODO + patched reference.md.)
- Audit current weak-stay impl (_stay_gt0_weak + _solid_stay_weak + the Rws call in _dashed) using Path C checklist + Path A/B grounding tests (can be done with a placed kr/testing/ script that enumerates words or uses Spot to check specific configs/words, without changing the core formula builders yet).  [Audit tool stabilized in first increment; now reports CLEAN on structural + semantic drift; use it to gate/drive each small algo edit.]
- Add the G(p ∨ F q)-style canary + semantic validator skeleton to testing/ (as P0/P3 items).
- Once (improved) audit passes on a change, *then* commit (one file per commit, test placed r4_audit + zoom + reconstruct on canary before, update STATUS/TODO before commit).
- Next code increments: small targeted fixes in reachability_operators.py (e.g. fix target config passed to reach_weak in Rws0 line1 c2/c3 to use T' / arrived per ref; clean special U case in not-bad+target of _solid_stay_weak; ensure case handling + recursion match pseudocode exactly). Verify each with timeout audit (must stay CLEAN or improve canary), zoom on G(p|Fq), basic reconstruct on Fa/a + canary.
- Sync other docs.
- Re-run full test matrix (zoom + reconstruct on expanded CASES including new canaries) under the 5s/ placed-script discipline.
