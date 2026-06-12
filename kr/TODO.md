# kr/ TODO

Forward-looking work items only. Current state: `kr/STATUS.md`. History: `git log`.
Construction reference: `paper/automata-to-ltl-construction.md`; ground truth:
`paper/Automata2LTL.txt` (Sec 4.2 + Table 1 + Formulas 3/4/5 ≈ lines 440–1040).

Context for prioritization: the FoSSaCS construction is implemented and
semantically validated (see STATUS). The thesis we are now chasing is that the
paper's double-exponential is a *flat-rendering* artifact: every case measured
so far builds a small hash-consed DAG in fractions of a second while only the
unfolded tree/string explodes. P0 below is the work that turns that
observation into a usable pipeline (and a SOTA claim).

## P0 — practice beats the bound (active)

Analysis, measurements and OPEN questions behind these items live in
`kr/dag_folding.md` (item numbering there: plumbing → vacuity pruning →
fold pass → interning). Items below are the actionable queue.

1. **Fold pass — step A DONE 2026-06-12** (per-DAG-node memoized
   tl_simplifier, hybrid full≤2000-nodes/basics policy + reach dead-tail
   early-out): `G(p->(qUr))` distinct temporal 4115→559, `G(a->Xb)` tree
   85.5M→3.6M, `a&Xa` subproblems 752→311. Remaining candidates, in the
   order the tail-anatomy data suggests (probe_tail_anatomy.py: TAILS drive
   the explosion — ×2–10 distinct tails per level — not the avoid web):
   - ~~**B. letter fusion**~~ **DONE 2026-06-12** (soundness:
     dag_folding.md "Letter fusion"; numbers: STATUS — XXa/XXXa collapse
     to the literal formulas, 3 survey cases flip True, G(a->Xb) under
     the acc cap). Remaining wall is fusion-neutral cases (1 AP, all
     letters distinct futures): `X(a&Xa)` 3.1×10¹⁰, `G(a->Xa)` 11.3M —
     they need C/D/E below or the 1c rewrite pass.
   - **C. cascade-aware vacuity pruning** of the combined-letter enumeration
     (unreachable pre-configs, empty Enter/Stay) — prunes memo keys at the
     b^k base; soundness argument needed (see dag_folding.md OPEN).
   - **D. tail normalization** (canonical letter-word prefix + continuation
     form) — syntactic, internal, targets the wrapping count directly;
     expected partially subsumed by B (fewer distinct tails by construction).
   - **E. budgeted semantic interning** of small subterms.
1c. **Own syntactic rewrite pass — IN PROGRESS (kr/simplify/, 2026-06-12).**
   Rule 1 (context pass: sibling-context propagation over the boolean
   skeleton, identity domination incl. temporal nodes, Shannon at Or,
   context reset at temporal boundaries) DONE + validated
   (kr/simplify/testing/test_context_pass.py, 16/16 with per-case Spot
   equivalence). Rule 2 (now-evaluation: one-step unroll of G/F/U/R/W/M
   heads under boolean context, shrink-only, identity + BDD entailment)
   DONE + validated (test_now_eval.py, 18/18). Rule 3 (partial factoring,
   the sound form + Minato minimization of guard groups) DONE + validated
   (test_factor_pass.py, 10/10 incl. the draft-bug regression).
   ~~Pipeline integration~~ **DONE 2026-06-12** (KR_SIMP_OWN per-node hook
   in _simp_f, persistent memos, size cap 2000, shared bdd_dict; numbers
   in STATUS — gates green, fuzz 1500 ALL EQUIVALENT). Refinement queue:
   - **eventuality-aware rewriting**: rewrites create temporal-body
     variants that RAISE the distinct-eventuality census (F(a&Xb) back
     over the 32-acc cap, G(a->Xb) 85→94); accept a rewrite only when it
     does not add distinct temporal nodes, or intern variants (item E).
   - giant nodes are skipped by the cap, so the X(a&Xa)/reactivity wall
     is barely moved — needs either O(n) factoring on big Ors or the
     C/D/E fold candidates.
   - the 32-acc abort path in equiv children dies with free(): invalid
     pointer (teardown, cosmetic but masks the real verdict — make the
     harness report it as ACC_CAP). Background
   (user rule set, Java lineage): Spot's
   tl_simplifier, even at full strength on 5-node inputs, does NOT do
   present-literal cofactoring or guard factoring: `a & (!a | G(!a|Xa))`
   (≡ Ga) and `(!a & Xa) | (a & Xa)` (≡ Xa) both survive full simplify
   untouched (probe_guard_fusion part A). Candidate rules, sharing-aware
   per DAG node (the "grow our own rule set" hatch in ltl_builders):
   (i) cofactoring `a ∧ (¬a ∨ φ) → a ∧ φ`; (ii) Or-factoring
   `(g₁∧Xt) ∨ (g₂∧Xt) → (g₁∨g₂)∧Xt` + Minato guard minimize (catches
   tails that become equal only after simplification, which construction-
   time fusion cannot see); (iii) induction `x ∧ G(x→Xx) ≡ Gx` (riskier,
   parked separately).
2. ~~**Output representation**~~ **DONE 2026-06-12**: reconstruct returns the
   hash-consed `spot.formula` DAG; flattening is opt-in (`reconstruct_ltl_str`
   historical entry, `_str_f_gated` under `KR_FLATTEN_TREE_LIMIT`). The former
   CONSTRUCT_TIMEOUT cases now report measured sizes in seconds (`G(a->Xa)`:
   5.1×10¹¹ tree nodes from ~2k DAG nodes). This is the native input for the
   planned BDD-style analysis layer.
3. **Verification beyond Spot translation — now the verification front**:
   compositional checking (trace_fin is the per-sub-term oracle),
   word-sampling validator (ultimately-periodic u·v^ω, construction-ref
   pitfall #10), equivalence-based interning of subterms. Probed and CLOSED
   (2026-06-12, `probe_object_translate.py`): translating from the formula
   OBJECT (Couvreur fm / translator class) does not dodge the wall — one acc
   set per distinct eventuality (cap 32 compile-time) and the tableau state
   space is subformula SETS, which sharing doesn't shrink. So: either fold
   the distinct-eventuality count below 32 (item 1 + interning), or verify
   without translation. Spot authors are in the loop on sharing-aware
   translation; revisit when they ship anything.

## P1 — coverage

- Full acceptance dispatch per construction-ref §9.3 (looping-Büchi/coBüchi
  direct Σ₁/Π₁ forms, Büchi/coBüchi Π₂/Σ₂ forms, weak Δ₁ end_in(G)) instead of
  always going through the Muller DNF; keeps outputs in the matching
  hierarchy class.
- π-preimage exactness in the non-primary paths: `accepting_configs` and the
  config_graph fallbacks still map states through the lift only (the primary
  pruned-config-aut path is already correct via `state_of` = π). With covers
  real (duplicated sinks), the fallbacks should classify every closure config
  through π.
- Trivial (size-1) level collapse to reduce effective depth.

## P2 — feasibility

- Larger |AP| (on-demand letters or BDD guards instead of explicit 2^k —
  8 letters already multiply the combined-letter fan-out visibly).
- Hierarchy class tagging of outputs (Σᵢ/Πᵢ/Δᵢ per Lemma 5).

## P3 — testing & docs

- Extend semantic grounding from fin_c sub-terms to arbitrary reach calls
  (GT automaton for "reach T from S avoiding B" with β/τ obligations).
- More multi-level round-trips + size/depth metrics vs paper bounds (the
  DAG-vs-tree table in STATUS is the seed of the empirical argument).
- Finite-word variant (weak next in wsolid, construction-ref §10) — stretch.
- Counter-free verification for external HOA inputs (GAP IsAperiodic) — stretch.
