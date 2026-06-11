# kr/ TODO

Forward-looking work items only. Current state: `kr/STATUS.md`. History: `git log`.
Construction reference: `paper/automata-to-ltl-construction.md`; ground truth:
`paper/Automata2LTL.txt` (Sec 4.2 + Table 1 + Formulas 3/4/5 ≈ lines 440–1040).

## HANDOFF — where debugging stands (written at end of 2026-06-11 session)

**What just happened:** All five operators were rewritten to the LITERAL paper
forms (see STATUS "Operators"). The former approximations (from-S letter
enumeration, first-step recursion, bespoke weak forms, wrong weak base) were
the 2L breakers — each was found by semantic grounding with witness words, and
each fix was verified against `paper/Automata2LTL.txt` directly.

**Examples used and why they fail/pass:**
- `GFa` (1L, 2 states, ι==C) — the minimal Fin-postponement canary. GROUNDED OK.
- `G(a -> X b)` (2L [2,2], safety; states: (1,1) init, (1,2) obligation, (2,1)
  sink) — first 2L target. Diagnosis chain that fixed it: (i) `r_to((1,1)→(2,1))`
  was `false` because no letter from S enters top 2 (entry fires only from
  lower config (2)) → combined-letter enumeration over ALL configs + lower-level
  prefix reach (solid⁺/Formula 5 literal); (ii) the remaining `r_with` failure
  (witness `a&b; !a&b; !a&b; cycle{a&b}`) was in the leave-avoid conjuncts —
  cursor-1 reaches with a REAL bad config exercising the weak cluster for the
  first time (1L never passes B≠None at top) → literal wreach dual + wsolid⁺.
  Now: ALL SUB-TERMS GROUNDED OK.
- Probe script for that diagnosis: `kr/testing/probe_2l_rwith.py` (drills into
  solid⁺ last-step disjuncts and checks each conjunct against the witness word).

**P0-perf step 1 DONE (2026-06-11, this session):** operators + fin_c +
assembly are `spot.formula` objects end-to-end (str accepted at entry for
probes); one shared `spot.tl_simplifier` with persistent cache, at most one
simplify per operator return; `_str_f` no longer simplifies; fin_c computed
once per config in assembly; sentinel guard removed. Validated: GFa +
G(a->Xb) ALL GROUNDED OK, audit CLEAN (patterns 1+5 updated to new shapes),
probe witness passes, survey: `a U b`, `Fa|Gb`, `Fa&Gb`, `Ga|Fb` flip True.
Measured (measure_formula_dag.py): G(a->Xb) builds in 0.08s, 781 DAG nodes,
3.2MB only as flat string (1600x unfolding). A dedicated reach_weak memo
looks unnecessary now (its inner reach_strong is lru-cached; ¬+simplify is
amortized by the persistent simplifier) — revisit only if profiling says so.

**Exact next steps (P0-verify — equiv checking, then semantics):**
1. `G(a->Xb)` (and anything ≥ its size) cannot be equiv-checked by translation:
   126 distinct temporal subformulas → Spot hard error "Too many acceptance
   sets used. The limit is 32" (fast fail, not a stall). Reduce DISTINCT
   temporal subterms: prune vacuous conjuncts (Enter(b)=∅, unreachable pre),
   per-subformula equivalence-based interning (canonicalize language-equal
   subterms to one representative); and/or check compositionally (trace_fin
   grounding is already the per-sub-term oracle) or by word sampling
   (u·v^ω, construction-ref pitfall #10).
2. New minimal failing case from survey: **`Ga | Gb` equiv=FALSE** (safety,
   sizes=[1,4], trivial size-1 top level — suspect the level-collapse /
   trivial-level handling). Diagnose with ltl_diff (containment + witness)
   then trace_fin grounding.
3. `F(a & X b)`: TIMEOUT >45s — find out whether construction or translate;
   if translate, same as item 1.
4. Then: `G(p -> (q U r))` (user request), then 3L (`Xa`).

## P1 — coverage

- Full acceptance dispatch per construction-ref §9.3 (looping-Büchi/coBüchi direct
  Σ₁/Π₁ forms, Büchi/coBüchi Π₂/Σ₂ forms, weak Δ₁ end_in(G)) instead of always going
  through the Muller DNF; keeps outputs in the matching hierarchy class.
- Muller lift exactness for n>2 levels (h⁻¹ powerset lift with SCC pruning + dedup).
- Trivial (size-1) level collapse to reduce effective depth.
- Remove/make-dynamic the >3L dev guard once multi-level is correct.

## P2 — feasibility

- Simplify at every construction step (inside R*/Fin builders), not only post-hoc.
- Systematic early-outs (Enter(t)=∅ ⇒ dashed false; Stay(s)=∅ ⇒ solid τ/false).
- Larger |AP| (on-demand letters or BDD guards instead of explicit 2^k).
- Hierarchy class tagging of outputs (Σᵢ/Πᵢ/Δᵢ per Lemma 5).

## P3 — testing & docs

- Extend semantic grounding from fin_c sub-terms to arbitrary reach calls
  (GT automaton for "reach T from S avoiding B" with β/τ obligations — needed for
  the 2L ladder work above).
- Word-sampling validator (ultimately-periodic u·v^ω: automaton acceptance ⇔ formula,
  per construction-ref pitfall #10).
- More multi-level round-trips + size/depth metrics vs paper bounds.
- Finite-word variant (weak next in wsolid, construction-ref §10) — stretch.
- Counter-free verification for external HOA inputs (GAP IsAperiodic) — stretch.
