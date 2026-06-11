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

1. **Own sharing-aware fold pass** (replaces nothing — Spot's tl_simplifier is
   out of the hot path by policy). Constructor-level rewrites + vacuous-
   structure pruning on the hash-consed DAG: dead/sink-routed tails, duplicate
   avoid-conjuncts, Formula-5 early-outs (Enter(t)=∅ ⇒ dashed false,
   Stay(s)=∅ ⇒ solid τ/false, unreachable pre-configs). Success metric:
   distinct temporal subformulas of `G(p->(qUr))` (currently 4115 for a
   3-state property) drop toward what its automaton warrants; secondary:
   DAG nodes / unfolded size shrink across the ladder.
2. **Output representation — now the TOP item**: reconstruct's str() contract
   is the bottleneck for 7 of the 11 non-True ladder cases (post guard-drop
   survey), including mid-size `G(a->Xa)` which flipped True →
   CONSTRUCT_TIMEOUT when tl_simplifier left the hot path (its construction
   is instant; only the final flat str() blows the budget). Carry
   `spot.formula` objects to callers (str on demand only), and/or a DAG-aware
   output format. This also feeds the user's planned BDD-style analysis
   layer for the formulas — solve naively first, shortcuts after.
3. **Verification beyond Spot translation** (32-acc-set limit / timeouts on
   100+ distinct temporal subterms): compositional checking (trace_fin is the
   per-sub-term oracle), word-sampling validator (ultimately-periodic u·v^ω,
   construction-ref pitfall #10), equivalence-based interning of subterms.
   Spot authors are in the loop on sharing-aware translation — our DAGs are
   the ideal client; revisit when they ship anything.

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
