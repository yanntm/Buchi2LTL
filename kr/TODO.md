# kr/ TODO

Forward-looking work items only. Current state: `kr/STATUS.md`. History: `git log`.
Construction reference: `paper/automata-to-ltl-construction.md`; ground truth:
`paper/Automata2LTL.txt` (Sec 4.2 + Table 1 + Formulas 3/4/5 ≈ lines 440–1040).

## P0 — multi-level correctness (drive with the 2L ladder, weakest MP class first)

Ladder: `G(a -> X b)`, `Ga | Gb` (safety) → `a U b`, `F(a & X b)` (guarantee) →
`Fa | Gb`, `Fa & Gb`, `Ga | Fb` (obligation). Method: extend/aim the semantic
grounding tools (trace_fin_semantics-style GT automata + ltl_diff witnesses) at the
reach terms of a failing case, find the first sub-term that diverges, fix against the
paper text, re-run audit + survey (no regressions), commit.

- **R5 line(2) exact shape.** Current `_dashed_change_strong` line(2) iterates
  Enter(t) instead of Enter(b), and conjoins `(η ∧ X(weak))` directly instead of the
  paper's parameterized-bad reach `S ~_{R(η ∧ X(wsolid(δ(⟨R,·⟩,η), ⟨T,t⟩, τ, ⟨B,b⟩, β)))}
  T'(σ ∧ X(inner))` (note the swap). Irrelevant when B=None (all Fin calls — why 1L
  works), but bad configs are real in nested solid⁺ avoid conjuncts.
- **From-S lower-context approximation.** Enter/Stay/Leave are evaluated from S only
  (`compute_stay_leave_from(S)`, `_enter_letters_at_level(S, ...)`); the paper
  enumerates combined letters ⟨σ,L⟩ with the lower config at firing time tracked by
  the lower-level recursion (`reach(S, …, T', σ ∧ Xτ)` reaches the firing point).
  Exact at 1L; likely the main 2L breaker (e.g. `a U b` → "b").
- **Solid⁺ exact conjunct structure.** Verify `_stay_gt0_strong` against the paper's
  solid⁺: per ⟨σ,T'⟩ ∈ Stay(s) with δ(⟨T',s⟩,σ)=⟨T,t⟩: free-reach conjunct +
  Leave-avoid conjuncts (reach(S, L, η, T', σ∧Xτ)) + bad-predecessor conjuncts
  (reach(S, B', ρ∧Xβ, T', σ∧Xτ)). Same for the U-form shortcut in `_solid_stay_strong`
  (S==T case) — verify it against the four-case dispatch or replace with literal
  `P ∨ τ`.
- **reach_weak shape.** `_dashed_change_weak` is a crude `G(stays | tau)`
  approximation; per paper, wreach is simply `¬reach(S, T, τ, B, β)` (swap). Consider
  implementing the dual literally and dropping the bespoke weak dashed/solid mirrors
  where the paper doesn't define them.

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
