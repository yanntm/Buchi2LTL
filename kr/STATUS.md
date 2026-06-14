# kr/ Current Status

Factual snapshot of the current state. History lives in `git log`; work items in
`kr/TODO.md`; doc map in `kr/README.md`.

**Bottom line: the FoSSaCS'22 construction is implemented end-to-end and
semantically validated.** The five reachability formulas are the literal paper
forms over a genuine SgpDec holonomy cascade; the MP-class ladder shows zero
semantic failures up to the 3-level dev guard. The open front is no longer
fidelity — it is output representation and verification at scale: the
construction produces small hash-consed DAGs in fractions of a second, and
everything expensive (Spot translation, flat strings) is an artifact of
unfolding that DAG.

## Pipeline

- `decompose_aut`: Spot norm to det complete min-even parity with **state-based
  acceptance** (`sbacc` — soundness requirement: the Muller condition is lifted
  over configurations, so the infinitely-visited state set must determine
  acceptance) → generators (explicit 2^|AP| letters) → GAP/SgpDec holonomy →
  parsed `Cascade`.
- **True-cascade extraction.** The GAP script emits (i) state lifts via
  `AsHolonomyCoords(s, sk)`; (ii) the genuine transitions: generators lifted
  with `AsHolonomyCascade` acting via `OnCoordinates`, BFS-closed from the
  lifts (TRANS lines); (iii) the cover map π via `AsHolonomyPoint` (PI lines).
  Holonomy coordinatization is a many-to-one **cover**: the closure can be
  strictly larger than the lift image (duplicated sinks etc.), and config
  dynamics must come from these lifted transitions — they are NOT the
  h-conjugation of D (that shortcut yields non-reset "cascades"; soundness
  precondition checkable with `probe_reset_consistency.py`). Parse REVERSES
  coordinates: SgpDec is top-first (deeper levels read upper state), the
  operators peel index 0 first with the suffix as the self-contained
  sub-cascade. GAP RNG is seeded → decompositions are reproducible.
- `Cascade`: levels, state↔config (1-based), letter valuations, `move_config`
  (explicit transition table; legacy h-conjugation only as fallback for old
  outputs), Enter/Stay/Leave helpers, pruned config automaton, accepting
  configs. `config_to_state` is π (total on the closure); `state_to_config`
  is the lift section.
- Good Muller sets: enumeration of strongly-connected **accepting subsets** of
  non-rejecting SCCs of the pruned config aut (`acc().accepting(in-M edge-mark
  union)` oracle, exact under sbacc; `KR_MULLER_SCC_LIMIT=12` gate, logged
  whole-SCC fallback).
- Stability: `bdd_utils` buddy-var precompute + per-case subprocess isolation
  in tests.

## Operators — literal paper forms, fast

- All five formulas are the literal constructions of paper Sec 4.2 /
  construction-ref §7: solid⁺ last-step decomposition with combined letters
  ⟨σ,T'⟩ over all closure configs and Leave-avoid/bad-predecessor conjuncts;
  Formula 5 lines (1)+(2)+(3) with the swapped wsolid in line (2) and no s==t
  guard; `reach_weak` = the literal dual ¬reach(S,T,τ,B,β); literal
  wsolid/wsolid⁺; `fin_c` per Lemma 7 with ι==C postponement. Case dispatches
  compare FULL configs.
- **Hash-consed `spot.formula` objects end-to-end, INCLUDING the output**:
  `reconstruct_ltl_paper_style` / `reconstruct_bls` return the
  formula DAG (str accepted at entry for probes). Flattening is opt-in only:
  `reconstruct_ltl_str` (historical entry), or the size-gated `_str_f_gated`
  (`KR_FLATTEN_TREE_LIMIT`). `PAPER_MAX_LTL_SIZE` now reports unfolded-tree
  node count, not string chars. The non-Muller `build_phi` string sketches
  were deleted (NotImplementedError → TODO P1).
- **Fully memoized:** `reach_strong` (lru) AND the five helpers (decorator
  keyed ⟨helper, casc, S, B, β, T, τ, level⟩) — one expansion per distinct
  subproblem, BDD-style. The runaway guard counts DISTINCT subproblems
  (`KR_REACH_GUARD`, default 5M).
- **Letter fusion (2026-06-12, the "B" iteration — dag_folding.md
  counter-measure B, default ON, `KR_FUSE_LETTERS=0` restores the
  per-letter literal shape).** At every enumeration site (solid⁺/wsolid⁺
  last-step/leave/bad-pre, dashed enter_t/enter_b/line-3, fin's
  `_uncond_reach_strict`) the summand reads the letter only through its
  guard, so letters are grouped by the `_dedupe` key minus `li`
  (enter sites key on the arrival too) and each group emits ONE summand
  whose guard is the Minato-minimized OR (`_fuse_or` in ltl_builders:
  BDD round-trip via `spot.formula_to_bdd`/`bdd_to_formula`,
  process-lifetime bdd_dict, plain-Or fallback). One tail per outcome
  class instead of per letter — the distinct-tail driver shrinks at the
  source. Soundness argument: dag_folding.md "Letter fusion". Measured:
  `XXa`/`XXXa` collapse to the LITERAL formulas (3/4 tree nodes; XXXa was
  SPOT_TIMEOUT); `Xa` output is `Xa`; `G(a->Xb)` tree 3.6M→22.6k and
  distinct temporal 226→85 (under the 32-acc-set cap → equiv=True);
  `G(p->(qUr))` tree 84.8M→55k, 559→121; `G(a->Xa)` 5.1×10¹¹→11.3M;
  `(a U b)|Gc` 2⁶⁰-saturated→528M; `X(a&Xa)` 6.3×10¹³→3.1×10¹⁰ (the
  remaining ladder wall). Survey: 3 cases flipped to True (`XXXa`,
  `G(a->Xb)`, `Ga|Gb`), zero regressions; grounding: zero contradictions;
  audit CLEAN. Post-fusion log: `kr/testing/logs/fusion_measure_dag_*`.
- **Own rewrite pass wired (2026-06-12, the "1c" iteration — kr/simplify/
  package, KR_SIMP_OWN=1 default, size cap KR_SIMP_OWN_LIMIT=2000,
  KR_SIMP_OWN_FACTOR toggles rule 3).** Three rules Spot lacks (validated
  standalone 44/44 + 1500-formula random fuzz ALL EQUIVALENT, oracle
  self-tested): (1) context pass — sibling-context propagation over the
  boolean skeleton, identity domination incl. temporal nodes, Shannon at
  Or, reset at temporal boundaries; (2) now-evaluation — one-step unroll
  of G/F/U/R/W/M heads under boolean context (initial-state knowledge,
  Bonneland et al. lineage), two-tier entailment (identity + BDD);
  (3) sound partial factoring + Minato guard groups. Hooked per node in
  `_simp_f` after Spot's pass (one bounded Spot re-pass when rules fire);
  persistent package memos make it amortized O(1) per distinct node; ONE
  shared bdd_dict per process (a second dict next to the fusion one
  corrupted the equiv-child heap). The size cap exists because the
  uncapped pass sent 3 reactivity cases CONSTRUCT_TIMEOUT — capped, all
  construction times are healthy. Measured (capped, vs post-fusion):
  `Ga`→`a & G(!a|Xa)`, `Fa`→`a | F(!a&Xa)`, `a&Xa`→literal `a & Xa`;
  `G(a->Xb)` tree 22.6k→12.2k; `G(p->(qUr))` 55k→38.7k; `G(a->Xa)`
  11.3M→2.0M; `(aUb)|Gc` 528M→7.7M; giants barely move under the cap
  (`X(a&Xa)` 31G→27.9G). Survey 24 True / 0 FALSE; audit CLEAN; grounding
  zero contradictions. KNOWN regression: rewriting creates temporal-body
  VARIANTS that coexist across branches, raising the distinct-eventuality
  census — `F(a&Xb)` went back over the 32-acc cap (its equiv child then
  dies in the abort path's teardown: `free(): invalid pointer` — infra,
  not semantic). Refinement item: eventuality-aware rewriting (TODO 1c).
- **Unroll-inverse fold pass (2026-06-12, the "rule 4" iteration —
  kr/simplify/fold_pass.py, KR_SIMP_OWN_FOLD=1 default).** Eight pair-folds
  (expansion laws backwards, arbitrary subformulas): `c|XFc→Fc`,
  `c&XGc→Gc`, U/W/R/M one-step forms, first-occurrence `c|F(¬c&Xc)→Fc`,
  induction `c&G(¬c|Xc)→Gc`; plus S1/S2 sibling subsumption (Formula-5
  line redundancy): `c|X(cRd)|G(c|Xd)→c|X(cRd)` and dual
  `c&X(cUd)&F(c&Xd)→c&X(cUd)` (proofs in module docstring; M/W variants
  UNSOUND, regression-tested; the one-step-SHIFTED ladder variants are
  genuinely not redundant — witness `!a; a; cycle{!a}`). Validated:
  test_fold_pass 26/26, all suites CLEAN, fuzz 3×500 ALL EQUIVALENT zero
  growth, audit CLEAN. Measured (vs post-1c): `F(a&Xa)` census 55→33 /
  tree 4611→901 / DAG 269→156; `F(a&Xb)` 109→87; `G(a|Xb)` 94→82;
  `G(a->Xa)` 193→147, tree 2.0M→1.5M. Survey: **`G(a->Xb)` flipped
  SPOT_TIMEOUT→True (25 True / 0 FALSE)**, `(aUb)|Gc` 7.7M→6.6M,
  `X(a&Xa)` flatten-gate census 23.1G→13.3G (NB measure_formula_dag's
  unfolded count for that case moved 52.6M→127M — fold changes memo keys
  and thus the construction path; DAG and temporal census both improved).
  Diagnosis tool: `kr/testing/probe_dag_dump.py` (let-binding DAG view +
  temporal census; the F(a&Xa) dumps that drove the rules are in
  `kr/testing/logs/faxa_dag_dump*.txt`).
- **Initial-state opening + context-aware subsumption (2026-06-13).**
  Three additions on top of rule 4. (i) Context OPENING (context_pass):
  temporal siblings feed their now-component into the context — Gφ
  asserts conj(φ), R/M assert conj(g); at Or, Fφ refutes disj(φ), U/W
  refute disj(g). Opened facts flow ONE-WAY (earlier→later in canonical
  child order): bidirectional opening built circular support and was
  caught UNSOUND by fuzz (witness `!(b R (Gb & (b M Gb)))` → 0; the
  opened b erased the sibling b while the M consumed it) — one-way is
  sound by sequential replacement; regression cases in
  test_context_pass. (ii) G/F ABSORPTION (fold_pass): conjuncts implied
  by a sibling Gφ dropped (small recursive entailment: X/F/G bodies,
  U/M arms, And/Or), dual at Or. (iii) **Context-aware S1/S2**
  (fold_pass.ctx_subsume, hooked as bool_hook into the context pass):
  under ctx ⊨ ¬c the S1 bare-c case is discharged by knowledge, so the
  unshifted AND the one-step-SHIFTED ladder forms fold — the shapes that
  are provably NOT redundant in isolation. **This pushed `F(a&Xa)` under
  the 32-acc cap: census 33→26, Spot equiv True end-to-end.** Measured:
  `F(a&Xa)` DAG 156→111, tree 901→453; `F(a&Xb)` census 87→74;
  `G(a|Xb)` 82→79, tree 6.8k→3.1k; survey `X(a&Xa)` flatten census
  13.3G→1.5G. Gates: suites 19/18/10/38 CLEAN, fuzz 3×500 ALL
  EQUIVALENT, audit CLEAN, survey 25 True / 0 FALSE. Known limitation:
  one-way flow + canonical order misses openings whose source sorts
  after the target (alternating direction across the pipeline's repeated
  context passes would be sound — TODO).
- **Census anatomy + arm-padding removal (2026-06-13).** Two probes
  answered "where does the residual census live?" conclusively
  (`probe_census_classes`, `probe_muller_overlap` — both committed):
  (i) the post-rules census is ~all genuinely distinct languages
  (F(a&Xa) 26/26 classes, F(a&Xb) 74→73, G(a->Xa) 144→≤126), so
  formula-level interning has little headroom; (ii) the Muller DNF is
  NOT the driver — disjuncts share 83% of the census via hash-consing
  (G(p->(qUr)): two disjuncts, 77 census each, overlap 70, whole 84);
  (iii) **the Fin(C)/¬Fin terms ARE the driver**: per disjunct the two
  Fin conjuncts carry census ~50 each (DAG ~285 each) while the
  reach/invariant part is ~25 — including a census-1 conjunct that is
  LITERALLY language-equivalent to the target body (`p -> (q U r)`
  verified): the construction contains the small answer, buried under
  the Muller-acceptance scaffolding. This is the evidence base for P1
  (direct Σ₁/Π₁/Π₂/Σ₂ acceptance dispatch instead of the Muller DNF).
  Spin-off rule from the class probe (fold_pass, validated 42/42 +
  fuzz): **U/W/R arm-padding removal** — `(c & Xd) U g → c U g` when
  c ⇒ d and g ⇒ d (the Xd is implied by the U dynamics; dual for R;
  propositional-fragment entailment, sound one-way): G(p->(qUr))
  census 98→84. NB the formula must be written `q U r` WITH SPACES —
  `qUr` parses as ONE atomic proposition (an earlier "solved at 21
  nodes" reading of this case was that artifact).
- **Config-graph reach FALSE-cut: tried, NEGATIVE, reverted (2026-06-13).**
  Hypothesis: prune `reach_strong(S,·,·,T,·)` to `false` when the target is
  graph-unreachable from the source in the config automaton — a cheap, exact,
  Spot-free cut at the source of the σ∧Xτ ladder. Two corrections shrank it to
  nothing. (1) Soundness: the paper's avoid is β-guarded and STRICT-BEFORE
  arrival (`∀j∈[0..i). δ≠B ∨ w⊭β`, Automata2LTL.txt:573), so `T==B` does NOT
  imply false and walling B in the BFS is unsound — only avoid-FREE target
  reachability is sound. (2) The cut must be SUFFIX-projected, not full-config:
  at recursion level k the target is matched on `T[k:]` (the `level==n` base is
  `(¬β)Uτ`, dropping T), so a full-config cut is the k=0 case and is unsound at
  k>0. A read-only probe over the helper memo showed 30% "cuttable" full-config
  — but ~all of that was the unsound over-cut; the sound suffix-projected cut
  fires ~104×/41584 on `Xa & XXa` and changes DAG/tree/temporal census by ZERO,
  likewise zero on `G(a->Xb)`/`G(p->(qUr))`/`F(a&Xb)`/`Ga|Gb` (audit CLEAN, all
  equiv True throughout). Diagnosis, consistent with the census-anatomy finding
  above: the explosion lives in the **Fin(C) acceptance scaffolding, not in
  reach** — its redundancy is β/τ-obligation-driven, invisible to graph
  reachability. The free-tail collapse the user is after needs a Fin(C)-level
  recognizer (config in an absorbing accepting class ⇒ constant Fin term), not a
  reach cut. All code reverted; finding kept here.
- **Per-conjunct Fin-reachability fold: LANDED (2026-06-13, the Fin(C)-level
  recognizer the bullet above asks for — generalizes and replaces the
  absorbing-M fold).** `config_graph.configs_reachable_from(casc, M)`
  (delegated via `Cascade`, consumed in `reconstruct_ltl_paper_style`; default
  on, `KR_FOLD_FIN_REACH=0` restores the full Muller term). For a good Muller
  set M, keep `Fin(C∉M)` **only for C reachable from M** in the config graph;
  drop it for every C off M's forward cone. Soundness (per term): the
  `¬Fin(C∈M)` conjuncts force Inf⊇M, and the i.o.-set of a path in a finite
  digraph is **strongly connected**, so any C∈Inf is reachable from M within
  Inf; contrapositive, C unreachable from M ⟹ C∉Inf ⟹ `Fin(C)` — implied,
  droppable. Pure graph property, no containment check. **Subsumes the
  absorbing-M fold** (M absorbing ⟺ reach(M)=M ⟹ all `Fin(C∉M)` drop) and
  fires where absorbing did not (non-bottom M with a side/transient C off its
  cone). Two wins: (i) it prunes more conjuncts AND (ii) the kept-config set is
  decided BEFORE building `fin_c` — the explosive part — so dropped configs
  cost zero construction. **It bites the distinct-temporal census (the 32-acc
  driver), not just the unfolded tree** — unlike absorbing-only. Measured,
  no-fold→per-conjunct (absorbing-only in parens),
  `logs/survey_sizes_perconj_2026-06-13`: `a U b` tree 87→13 / temporals 4→1
  → the LITERAL `b | ((a&!b) U (a&!b&Xb))`; **`F(a&Xb)` tree 4251→2739 /
  temporals 74→64 (absorbing: 74, no change)**; `(aUb)|Gc` 637→525 / 22→18
  (abs 19); `Ga|Gb` 7026→6438 / 47→46 (abs: no change); `Fa&Gb` 187→159 /
  12→11 (abs: no change); `G(a->Xa)` 144→141; `X(a&Xa)` 4138→4134. Still over
  the cap where they were (`F(a&Xb)` 64>32), but the census is now moving on
  reach-driven cases. Audit CLEAN; survey 0 fail / no regressions. Open: the
  cap cases need deeper census reduction (the kept `¬Fin(M)` / reachable-`Fin`
  part still dominates — census-anatomy finding).
- **Acceptance dispatch — Büchi class WIRED on the default path (2026-06-13).
  The structural fix the census-anatomy finding pointed to, now live.**
  `kr/acceptance_dispatch.py` `reconstruct_buchi(casc)`: per Theorem 2 / §9.3 a
  deterministic **Büchi** cascade (`acc=Inf(0)`, `Π₂`) gets the DIRECT form
  `φ := ⋁_{C∈α} ¬Fin(C)` — NO `Fin(C∉G)` web and NO good-set enumeration (the
  two Muller-DNF explosions). Soundness: `¬Fin(C)` ≡ "C∈inf-set"; the inf-set is
  strongly connected, so Büchi `inf∩α≠∅` ≡ `⋁_{C∈α}¬Fin(C)` (a transient
  accepting C ⇒ `¬Fin`≡false, harmless).
  - **Wiring:** a TOP-LEVEL pre-check at the head of
    `reconstruct_ltl_paper_style` (gate `KR_DISPATCH_BUCHI`, default ON; `=0`
    restores pure Muller for A/B). The hook lives THERE — not in
    `reconstruct_bls` — because the GOTO decompose front end
    (`reconstruct_decomposed`) calls `reconstruct_ltl_paper_style` directly per
    piece; the single pre-check covers BOTH entries. It cannot fire inside the
    Muller DNF's own `fin_c` (that runs in the operators/`fin` modules, which
    never call back). Single-condition decompose pieces are exactly Büchi/coBüchi,
    so the dispatch fires per piece (e.g. `GFa&GFb&GFc` and(3): each conjunct
    dispatches).
  - **α is COVER-AWARE** (`config_graph.buchi_accepting_configs`, delegated via
    `Cascade`): read off `build_pruned_config_aut` — every reachable config whose
    lifted (sbacc) marks satisfy the same `g.acc()` oracle `accepting_sc_subsets`
    uses — NOT the lift-section `accepting_configs()` (one config per state). The
    lift section UNDER-approximates on a genuine holonomy cover: wiring first
    flipped `F(a&Xb)` to equiv=FALSE (`L(buchi)⊊L(orig)`, α missed the duplicated
    accepting sink), the cover reader gives the exact α={(1,1),(1,2)}. This is the
    caveat TODO P1 flagged, now resolved.
  - **Results (size A/B on the decompose path, `logs/sizes_dispatch_{on,off}_
    2026-06-13`; distinct temporals = 32-acc-cap driver):** `G(p->(qUr))`
    84→**14** (tree 20291→751, UNDER the cap → survey equiv=True — the challenge
    case); `G(a->Xa)` 141→30 (tree 1.53M→703); `G(a->Xb)` 79→23; `F(a&Xb)` 64→40;
    `Ga|Gb` 46→18; `GFa` 10→3; `GFa&GFb` 20→6; `GFa&GFb&GFc` 30→9; `X(a&Xa)`
    4134→2069 (still over the flatten gate — reach-driven, needs the reach fold
    not acceptance dispatch). Totals over 35 cases: DAG 61029→47498 (−22%),
    distinct temporals 10907→8491 (−22%); excluding the two giants the tractable
    cases drop 578→227 (−61%). No case grows; out-of-scope classes (coBüchi
    `FGa|FGb`, reactivity `GFa->GFb`, persistence, already-minimal recurrence) are
    byte-identical (clean fallback). **Survey
    (`logs/survey_wire_buchi_2026-06-13`): 0/35 equiv=FALSE, four walls flipped to
    True (`G(p->(qUr))`, `F(a&Xb)`, `G(a->Xa)`, `GFa&GFb&GFc`), zero regressions;
    audit CLEAN.**
- **Acceptance dispatch — coBüchi class WIRED (2026-06-13), the mirror of Büchi.**
  `reconstruct_cobuchi(casc)`: a deterministic **coBüchi** (persistence, `Σ₂`)
  cascade gets `φ := ⋀_{C∈α} Fin(C)` (α = the "visit finitely"/marked configs) —
  exact, since coBüchi acceptance is `Inf(ρ)∩Marked=∅` ≡ `⋀ Fin(C)` (a transient
  marked C ⇒ `Fin`≡true, harmless). Wired as a SECOND pre-check after Büchi in
  `reconstruct_ltl_paper_style` (gate `KR_DISPATCH_COBUCHI`, default ON), so it
  only sees genuinely-not-Büchi cascades. α = `config_graph.cobuchi_finite_configs`
  — the cover-aware DUAL of the Büchi reader (configs whose lifted marks make
  `g.acc()` REJECT). **GATE SUBTLETY (the crux, found UNDER decomposition — the
  raw `decompose_aut` view is misleading):** `decompose_aut`'s parity step turns
  the natural `Fin(0)` into `Inf(0)|Fin(1)`, on which `acc().is_co_buchi()` is
  False; the gate recovers the natural acceptance via
  `postprocess(.,"deterministic","generic")` and tests `is_co_buchi` there. The
  `postprocess(.,"coBuchi")` variant is UNSOUND — a recurrence cascade (`GFa`)
  passes it. **Results (`logs/sizes_dispatch_cobuchi_2026-06-13` vs the Büchi-only
  `..._on_...`, decompose path):** `FGa` 6→3 temporals, `F(a&Gb)` 7→4, `FGa|FGb`
  **6195→2779** (tree 1.15×10¹⁸→3.23×10¹⁷ — census >½ off, still over the flatten
  gate so UNVERIFIED, the residual is reach-driven not acceptance-driven), and the
  reactivity `(GFa&FGb)` 10→7 (its `FGb` AND-piece dispatches — composes with
  decomposition). Totals over 35 cases DAG 47498→28207, distinct temporals
  8491→5066 (both −40%). Survey (`logs/survey_wire_cobuchi_2026-06-13`): 0/35
  equiv=FALSE, the ONLY verdict change is `FGa|FGb`'s UNVERIFIED tree shrinking;
  audit CLEAN.
- **Acceptance dispatch — weak/looping (Δ₁/Σ₁/Π₁) WIRED but OFF by default
  (2026-06-13, `KR_DISPATCH_WEAK`, the experimental A/B baseline).**
  `reconstruct_weak(casc)` = `⋁ over accepting SCC G : end_in(G)`, with
  `end_in(G) = (⋁_{C∈H} reach_to(ι,C)) ∧ (⋀_{C'∈G'} ¬reach_to(ι,C'))` — pure
  `reach_to` (`reach_strong(ι,C,⊥,C,⊤)`), NO Fin; subsumes looping-Büchi (safety
  `⋀¬reach_to(sink)`) and looping-coBüchi (guarantee `⋁reach_to(sink)`). Gate
  `is_weak_cascade` = `is_weak_automaton(postprocess(.,"generic"))` (clean: all
  weak cases T, GFa/FGa/G(p->(qUr)) declined). Placed BEFORE Büchi/coBüchi (weak
  languages are Büchi AND coBüchi recognisable, so those would claim them first);
  fires only when the flag is set. Correct: flag-on survey
  (`logs/survey_weak_flagon_2026-06-13`) 0/35 equiv=FALSE. **But it is a SIZE
  REGRESSION and is therefore kept OFF** — `probe_weak_dispatch` /
  `probe_looping_dispatch` (both committed): the general form is worse on 6/7
  cases; dedicated looping is mixed (2 wins `Ga|Gb` 18→14, `F(a&Xb)` 40→30; 3
  losses `G(a->Xa)` tree 703→6263, `G(a->Xb)` 23→30, `a U b` 1→3). Root cause:
  weak languages are already handled smaller by Büchi/coBüchi, and the residual
  on these cases is **reach-driven** (the τ-tail), which NO acceptance form
  touches — looping merely swaps the Fin-web for `reach_to`, paying the same
  cascade depth. Kept in (flagged off) as the A/B baseline for the next idea: a
  config-indexed **`Acc(c)`** weak-class construction. **DONE — see next bullet.**
- **Config-indexed `Acc(c)` for the BOUNDED fragment — WIRED, default ON
  (2026-06-13). Cracks the `X(a&Xa)` reach wall: UNVERIFIED 5.1×10⁸ → equiv=True,
  literal output.** `reconstruct_acc(casc)` (`KR_DISPATCH_ACC`, default ON, FIRST
  in the dispatch chain). Reconstructed from the `dag_folding.md` "Key-space
  diagnosis" spec (the original POC was reverted uncommitted). `φ := Acc(ι)` by
  bounded unroll of the config graph: `Acc(c) = ⊤` if `L(D from state_of(c))` is
  universal, `⊥` if empty (R1, a small Spot ⊤/⊥ oracle on the INPUT automaton D —
  lazy + cached, NOT on the output); else `⋁_σ guard(σ) ∧ X Acc(move_config(c,σ))`
  (R2 unroll). **SELF-GATING:** a config re-entered on the unroll path that is not
  ⊤/⊥ is recurrent ⇒ Acc declines (None ⇒ caller falls back to the
  Büchi/coBüchi/Muller chain), so it fires only on the bottom/bounded class. It
  is the construction the census-anatomy/key-space diagnosis said was needed: it
  bypasses the reach machinery entirely (no reach_to, no Fin, no τ-tail), emitting
  the literal formula. Complexity is low: `O(|reachable configs| × |Σ|)` memoized
  builds plus ≤ n bounded oracle calls on the small `D` (the expensive Spot
  operation — translating the large output — is exactly what it avoids). Measured
  (`probe_acc_dispatch`): `X(a&Xa)` BLS 11835/5.1×10⁸/2069 → Acc **4/5/0**, equiv
  True; the whole X-ladder collapses to the literal; every recurrent control
  (`Ga`, `a U b`, `F(a&b)`, `G(a->Xb)`, `GFa`, `FGa`) declines → BLS. **Survey
  (`logs/survey_wire_acc_2026-06-13`): the ONLY verdict change is `X(a&Xa)`
  UNVERIFIED→True; 0/35 FALSE, zero regressions; audit CLEAN.** After this the
  only non-True case left was `FGa|FGb` (persistence-union absorption, recurrent,
  over the cap) — since cracked by the buchi2ltl gate (see the gate bullet
  below; MP survey now a clean sweep). **Scope measured** (`probe_acc_fuzz`, 3×60 randltl
  through the real workflow; report in `dag_folding.md` "Acc(c) config-indexing"):
  gate rate ~24% but the fired cases are almost all TRIVIAL (boolean / 1-2×X /
  bounded decompose-pieces) where BLS is already tiny — the high-value
  deep-bounded case (`X(a&Xa)`) is a rare tail random sampling misses. **Kept ON
  despite the narrowness** (cheap, self-declining, and it is the only thing that
  reaches the bounded reach wall). Caveat: Spot ⊤/⊥ oracle in the construction
  path (bounded, on the small input) — the one departure from "Spot for
  hash-consing only"; a structural sink-reachability test could replace it (TODO).
- **buchi2ltl heuristic gate — WIRED into the decompose dispatcher, default ON
  (2026-06-14). Cracks the last MP wall `FGa|FGb`; the MP survey is now a clean
  sweep.** `kr/heuristic_gate.py` `try_heuristic_gate(aut)` is the SINGLE seam
  between the two paths (the kr core operators import nothing from `buchi2ltl/`;
  the old "never mix" rule is retired). **Gate goes UNDER decomposition
  (`KR_GATE_UNDER_DECOMP`, default ON, 2026-06-14):** `decompose_recombine`
  splits FIRST and applies the gate only to the leaves that no longer split —
  so a decomposable input is always cut into pieces (each then gated or
  cascaded), even when the gate could take the whole. `=0` restores the old
  order (gate first at every node, short-circuiting the split). Exception kept:
  when the ROOT does not split, the gate runs on the RAW (pre-determinization)
  input — see "determinize-then-gate" below. This makes the reported technique
  honest: a case `split_report` says `or(2)` now actually decomposes
  (`tech=or+sl`), instead of being silently taken whole by the gate. Size
  effect is a wash (DAG 494→491, temporal 114→119): OR-unions get tighter
  (`Fa|Gb` tree 13→8 — strength split removes the `W`-tangle), AND-conjunctions
  get the un-factored form (`GFa&GFb` vs the gate-whole `G(Fa&Fb)`, +1 temporal),
  all far under the cap and stylistically equivalent.
  - **Soundness is a composition of sound steps, NO per-call equiv check:**
    arbitrary HOA →(Spot `postprocess` to TGBA, language-preserving)→ buchi2ltl.
    buchi2ltl's CORE is `sl` (self-loop backward labeling) — an EXACT
    state-elimination translation, exact precisely on the very-weak (1-weak)
    fragment (every cycle a self-loop) and DECLINING (`UNSUPPORTED`) elsewhere; its
    f2/t2 layer is a separate verify-before-use guess-and-check (propose an SCC
    fragment, validate by equivalence, then adopt). So adopted output is sound by
    construction, NOT by post-hoc checking — full description in the
    `kr/heuristic_gate.py` module docstring (authoritative; read it before
    re-reasoning about sl). The
    bounded equiv check is kept only as an OPT-IN audit (`KR_GATE_VERIFY`,
    default OFF; on, the gate re-checks every adopted candidate against its
    small node automaton and counts `rejected`). **Audited at scale
    (`fuzz_gate_decompose.py`, VERIFY=1, 3 seeds ≈170 randltl formulas / 191
    piece-adoptions): 0 equiv=FALSE, 0 rejections, ~81% adopt rate**
    (`logs/fuzz_gate_seed{1,2,3}_2026-06-14`). The bounded TGBA conversion is the
    same "Spot on the small input" departure already accepted for Acc(c) — never
    the translate-the-giant-output wall.
  - **Why determinize-then-gate is NOT enough (measured, `probe_gate_redet.py`,
    2026-06-14):** buchi2ltl's backward labeling exploits the (often
    nondeterministic) translate-style TGBA, which `_to_split_form`'s
    determinization destroys. Re-asking Spot for `TGBA,Small,High` off the
    determinized form does NOT recover a labelable automaton: `FGa|FGb` goes raw
    3-state nondet Büchi (`Inf(0)`, buchi2ltl ok tree=13) → det 2-state coBüchi
    (`Fin(0)`) → re-projected 4-state nondet Büchi that buchi2ltl DECLINES — a
    one-way loss. For every other surveyed case `raw`==`det` (translate already
    minimal) so it is moot. Hence the gate runs on the RAW input exactly when the
    root does not split (the determinization-sensitive cases are non-decomposable);
    decomposable inputs are split first and the pieces gated. Sound regardless:
    TGBA conversion is language-preserving.
  - **Adopted output is simplified through `_simp_f`.** buchi2ltl does NOT wire
    Spot's LTL simplifier, so its raw output is syntactically padded (`Fa|Gb`
    emits a 5-temporal form `((!a&b)U(a|...))|(G(!a&b)&GF(!a&b))` that
    simplifies to the 2-temporal `(!a&b)W(a|(!b&XFa))`). Every other kr node
    passes through `_simp_f`; the gate routes its candidate through it too so
    adopted formulas are on equal footing with the cascade. This removed two
    apparent obligation-case regressions (`Fa|Gb`/`Ga|Fb` raw 5→2) AND the `Fa`
    cosmetic enlargement; `probe_gate_inspect.py` shows the before/after.
  - **Results (size A/B on the decompose path, gate ON vs OFF,
    `logs/survey_sizes_gate_{on,off}_2026-06-14`; distinct temporals = 32-acc-cap
    driver):** `FGa|FGb` **2779→3** (tree 3.2×10¹⁷→6 — the last wall collapses);
    `G(a->Xb)` 23→1; `G(a->Xa)` 30→2; `Ga|Gb` 18→3; `GFa->GFb` 19→4;
    `GFa&GFb&GFc` tree 46→8 / 9→4; `(aUb)|Gc` 9→3; `Fa&Gb` 7→2. Totals over 35
    cases: distinct temporals **2997→114 (−96%)**, DAG 16376→494, tree
    3.2×10¹⁷→1951. **Zero regressions** (13 cases smaller, 22 unchanged, 0
    larger — `compare_sizes.py`). The earlier apparent `F(a&Xb)` regression was a
    same-process memo-contamination artifact in the test harness — the fresh
    per-subprocess census is 40 either way (gate declines it; kr carries it).
  - **Gates:** r4 audit CLEAN; MP survey `logs/survey_gate_buchi2ltl_2026-06-14`
    **0/35 equiv=FALSE, every case True** (the previously-failing set —
    `F(a&Xb)`, `G(p->(qUr))`, `G(a->Xa)`, `GFa&GFb&GFc`, `G(a->Fb)`/`G(a|Fb)`,
    `FGa|FGb` — all flip True). Gate `KR_GATE_BUCHI2LTL` (default ON; =0 restores
    the pure kr decompose path). Side-by-side comparison of the two paths:
    `testing/run_mp_through_buchi2ltl.py` (30/35 handled standalone, 0 FALSE; the
    5 it declines whole are carried by kr under the gate).
  - **Portfolio result struct (`kr.recon_result.ReconResult`, 2026-06-14).** kr
    is now a portfolio (gate / and-split / or-split / acc / weak / buchi / cobuchi
    / bls-Muller), so `reconstruct_decomposed` returns a `ReconResult` (`.formula`
    + `.technique`, a deduped SET of the method tags that contributed) instead of
    a bare formula. buchi2ltl's `reconstruct_ltl` returns the SAME struct (its
    `sl`/`t2`/`f2` tokens). The set is threaded by reference down the dispatch
    (MT-safe — no module-level recorder). Wired into both surveys' output as a
    `tech=` column; the leaf method is recorded inside `reconstruct_ltl_paper_style`
    (the only place it is known). API change: `reconstruct_decomposed(...).formula`
    at all call sites. (The `ReconResult` lives in `kr/` and buchi2ltl imports it
    lazily — a temporary cross-package edge to be lifted into a shared `util`
    later; no load-time cycle since `import kr` does not import buchi2ltl.)
  - **Contract reification — `status` (P-ARCH step 1, DONE 2026-06-14).**
    `ReconResult` now carries an explicit `status` (OK / DECLINED) with
    `ReconResult.decline()` / `.declined` / `.ok`; "not me" is no longer the
    `UNSUPPORTED` string smuggled inside `.formula` (engines still use that string
    INTERNALLY in their backward-labeling recursion — translated to DECLINED at the
    boundary return of `buchi2ltl.reconstruction.reconstruct_ltl`). Consumers branch
    on `.declined`: `heuristic_gate`, `sl_driven`, and the root CLIs
    (`buchi2ltl.py`, `evaluate.py`). The `Translator` Protocol (callable
    `twa -> ReconResult`; invariant: language-faithful OR declines, never wrong) is
    documented in `recon_result.py`. A transitional legacy-string sniff in
    `.declined` keeps each one-file commit green; drop it once no boundary emits the
    sentinel. Gates: r4 audit CLEAN, MP survey clean sweep
    (`logs/survey_parch_step1_2026-06-14.txt`). See TODO P-ARCH.
- **kr UNDER sl — full-suffix delegation prototype (2026-06-14; orthogonal:
  `kr/sl_driven.py` + one optional `buchi2ltl` hook). The mirror of the decompose
  gate; attacks BLS's state-count explosiveness by handing kr SMALLER automata.**
  `reconstruct_sl_driven(aut)` runs sl as the DRIVER; at any multi-state-SCC state
  (sl's hard case, bottom OR transient) it delegates the whole sub-automaton A_q
  to the normal `reconstruct_decomposed` (decompose + gate + cascade) and
  reattaches the label. sl does the very-weak envelope exactly + tiny; kr does the
  multi-cyclic core on a smaller automaton (kr cost ~ cascade depth ~ state count).
  - **Seam:** optional `scc_labeler` callback on the DAG-native engine
    `buchi2ltl.reconstruction.reconstruct_ltl` (the labeler returns a
    `spot.formula` DAG, spliced as a child node WITHOUT flattening). Delegation at
    the `label()` entry, keyed on multi-state-SCC membership (`spot.scc_info`), so
    it covers BOTH the bad_states and the `visiting` decline paths.
    Termination/no-ping-pong: delegated kr uses the sl GATE (no labeler) → declines
    the core → cascade; never re-enters the driver.
  - **Soundness:** the delegated label is L(A_q) = exactly the language sl's own
    label(q) represents, so a sound translator's label is interchangeable; the
    validated sl construction composes it (X-wrapped, invariants re-added). Probe
    `probe_sl_compose`: **0 equiv=FALSE.**
  - **Results (`probe_sl_compose`, `probe_sl_delegation`):** X-prefix envelopes
    are big wins — `XX(G(a->Fb))` kr-on-full **979 temporals → sl-driven 4**
    (sl-alone declines), `XX(F(a&Xb))` 464→40, `c U (G(a->Fb))` kr-on-full
    TIMEOUT/explode → sl-driven **5**. Mixed where the prefix entangles with the
    core (`a U (F(b&Xc))` 40 vs kr-full 30 — the until's multi-state SCC spans
    prefix+core so A_q ≈ whole).
  - **Boundary flattening — RESOLVED 2026-06-14 (buchi2ltl is now DAG-native).**
    Formerly buchi2ltl was STRING-based, so the delegated kr DAG was FLATTENED at
    the boundary via `str(reconstruct_decomposed(A_q))` — cost was the core's
    unfolded-TREE size, and a high-sharing core (small DAG, huge tree) would
    explode `str()` before sl ever saw it. `reconstruct_ltl` now builds a
    hash-consed `spot.formula` DAG end to end (t2 fragments included), and the
    `scc_labeler` returns the kr `spot.formula` DAG directly (no `str()`), spliced
    as a child node. The payoff shows in `probe_sl_compose`: `XX(G(a->Fb))`
    kr-on-full 5596 DAG / **1.2×10¹⁴ tree** → sl-driven **21 nodes**;
    `c U (G(a->Fb))` kr-on-full TIMEOUT/explode → sl-driven **28**; `XX(F(a&Xb))`
    kr-on-full 2957 DAG / **1.1×10⁹ tree** → 183. All equiv=True. The DAG engine
    was cross-oracled against the (now deleted) string engine across the MP ladder
    + randltl with 0 divergences; size census on the default decompose path is
    byte-identical to the pre-flush `gate_on` baseline (pure engineering refactor).
    The engine was folded into `reconstruction.py` (shared automaton helpers split
    into `reconstruction_helpers.py`); the parallel `reconstruction_dag.py` and the
    `probe_dag_oracle.py` cross-oracle were removed.
  - Not wired into any default path (a top-level chooser between the gate-path and
    sl-driven, plus a scale soundness fuzz, are later steps).
- **Per-DAG-node memoized simplification (2026-06-12, the "A" iteration).**
  `_simp_f` simplifies each hash-consed node ONCE (id-keyed memo + the shared
  tl_simplifier's internal cache); operators build bottom-up so every call
  sees already-simplified children. Policy `KR_SIMP_OPTS`: hybrid (default) =
  Spot's full rules only on nodes with unfolded size ≤ `KR_SIMP_FULL_LIMIT`
  (2000), basics (constant folding, X(0)→0) above — full's syntactic-
  implication pass is pairwise and sharing-blind and stalled >15s per-node on
  `X(a&Xa)`, basics never stalls. `KR_SIMP_NODE=0` = old identity behavior.
  Paired with the dead-tail early-out in reach_strong
  (`reach(…,τ≡false) ≡ false`, the Table-1 base case), folded tails delete
  their memo-key subtrees. Measured: `a&Xa` 752→311 subproblems; `G(a->Xb)`
  distinct temporal 538→226, unfolded tree 85.5M→3.6M; `G(p->(qUr))`
  distinct temporal 4115→559 (7.4x); `X(a&Xa)` max tail 177x smaller (counts
  −20% only — the residual is genuine b^k wrapping, see dag_folding.md).
  We still never WAIT on Spot: each call is one node with simplified
  children, and the escape hatch drops Spot from the path entirely.

## Validation state

The ≥4-level dev guard is GONE (opt-in `KR_MAX_LEVELS` ceiling remains; the
real runaway protection is the distinct-subproblem guard). Depth ladder
added: `Xa` 3L → `XXa` 4L → `XXXa` 5L → `X(a & Xa)` 5L.

- **MP ladder (decompose path, now the default — `survey_decompose_2026-06-13`):
  zero equiv=FALSE, zero regressions vs the monolithic baseline, and the
  acceptance-driven walls VERIFY**: `GFa&GFb`, `(aUb)|Gc`, `(GFa&FGb)`,
  `GFa->GFb`, `G(a->Fb)&G(c->Fd)` (L=7) all equiv=True; `XXXa` at 5 levels and
  `G(a->Xb)`/`Ga|Gb` end-to-end.
  - **With the buchi2ltl gate (default ON, 2026-06-14) the MP survey is a CLEAN
    SWEEP: every case equiv=True** (`logs/survey_gate_buchi2ltl_2026-06-14`),
    including the entire former residual — `F(a&Xb)`, `G(p->(qUr))`, `G(a->Xa)`,
    `GFa&GFb&GFc`, `G(a->Fb)`/`G(a|Fb)`, and the last wall `FGa|FGb`
    (persistence-union absorption, 2779→3 temporals). See the gate bullet above.
  - Pure-kr A/B (gate OFF, `KR_GATE_BUCHI2LTL=0`): the residual was the
    REACH/cascade-driven single-piece cases (`F(a&Xb)`, `X(a&Xa)`, `G(a->Xa)` —
    the P0 fold job) plus the acceptance-ABSORPTION `FGa|FGb` (folds to one
    co-Büchi, no split); the gate now carries all of them. Monolithic path
    (`KR_DECOMPOSE=0`) unchanged — the A/B confirms the wins are split + gate.
- **Semantic grounding (`trace_fin_semantics`, cover-aware — GTs on the config
  semiautomaton): zero contradictions across every probed case at every
  depth** (`GFa`, `a U b`, `Fa & Gb`, `Ga | Fb`, `Xa` fully OK; `G(a->Xb)`,
  `Ga|Gb`, `F(a&Xb)`, `G(p->Xq)`, `G(p->(qUr))`, `XXXa` 14 OK, `X(a&Xa)`
  11 OK — remaining sub-terms UNVERIFIED by size only). Every check Spot can
  complete is OK.
- Audit gate (`test_kr_r4_audit.py`): CLEAN.

## Open front: representation & verification at scale (not fidelity)

Full analysis, thesis and candidate counter-measures: `kr/dag_folding.md`
(research notes, deliberately open). Summary: the construction is cheap; the
flat form is not. Current measurements (`measure_formula_dag.py`):

| case | build | DAG nodes | unfolded tree | sharing |
|---|---|---|---|---|
| `G(a->Xb)` | 0.08s | ~1.2k | ~1.5M | >1200x |
| `Ga\|Gb` | 0.08s | ~1k | 2M | >2000x |
| `G(p->(qUr))` | 0.14s | 9k | 64.8M | 7179x |
| `(a U b)\|Gc` | 9.5s | (284k subproblems) | — | — |

Consequences: (i) Spot translation hits the 32-acceptance-set tableau limit
(one set per distinct temporal subformula; we carry 100s–1000s) or times out;
(ii) flat strings reach 100MB+ (one `G(p->(qUr))` fin sub-term: 108MB), so
the str() API contract itself becomes the bottleneck for the biggest cases.
All test scripts carry built-in Spot budgets (`KR_SPOT_EQUIV_TIMEOUT` /
`KR_CHECK_TIMEOUT`, 10s) and report SPOT_TIMEOUT / UNVERIFIED — never
conflated with semantic failure. Spot authors are in the loop on
sharing-aware translation (our outputs are the ideal client). The active work
items (TODO P0): our own sharing-aware fold pass, compositional +
word-sampling verification.

**Object-out API landed (P0 plumbing item, 2026-06-12).** With reconstruct
returning the DAG and harnesses flattening only under `KR_FLATTEN_TREE_LIMIT`
(survey default 5M tree nodes ≈ every case Spot equiv ever completed), the
former CONSTRUCT_TIMEOUT class became measured verdicts in seconds:
`G(a->Xa)` ~2k DAG nodes unfolding to **5.1×10¹¹** tree nodes (sharing
~2.5×10⁸); `(a U b)|Gc` saturates the counter at 2⁶⁰. Previously-True ladder
cases re-verified True; audit CLEAN.

**Native-operator basis: investigated and CLOSED (2026-06-12,
`probe_native_ops` — one-shot tool, lives in git history).** The former
"raw U sugar" observation was stale, pre-iteration-A. Measured: Spot's
constructors do NOT rewrite sugar (`U(1,a)` and `¬(a U b)` stay raw nodes),
but the per-node simplifier normalizes every node to negation normal form
even in basics-only mode (`¬(1 U ¬a)`→`Ga`, `¬(b U ¬a)`→`¬b R a`); since
the operators build bottom-up through `_simp_f`, **outputs are already in
the native G/F/R/W basis** — census of real outputs shows `Not` only over
atomic propositions, zero ¬-over-U anywhere. The surviving U nodes are
GENUINE strong eventualities (distinct `¬β U τ` base cases): 94 in
`G(a->Xb)`, 246 in `G(p->(qUr))` — the >32-acc-set driver is the genuine
eventuality count, which no operator-basis change can reduce. Reduction
must come from folding (TODO 1 B/C/D) or non-translation verification
(TODO 3). Baseline size censuses for the standard cases:
`kr/testing/logs/baseline_*_2026-06-12.txt`.

**Object-path translation is a dead end (probed 2026-06-12,
`probe_object_translate.py`).** Spot accepts our formula objects natively
everywhere (`ltl_to_tgba_fm`, `translate`, `translator` class — no string
round-trip), but Couvreur allocates one acceptance set per DISTINCT
eventuality: our 400–600 distinct temporal subterms blow the compile-time
`mark_t` cap (32 in system Spot 2.14.5) instantly, and `Ga|Gb` ground >10s in
the tableau before even reaching the cap — the tableau's state space is sets
of subformulas, which hash-consing does not shrink. Verification must come
from word sampling / compositional grounding (TODO P0), or from folding the
eventuality count itself below the cap.

**Decompose-and-recombine at the root: LANDED + made the GOTO path (2026-06-13,
`kr/decompose_recombine.py` — orthogonal module, core untouched).** ROOT-level
language operations recombine kr outputs soundly with no caveats (kr is
language-faithful, a root operator is a pure position-0 language op — none of the
temporal-placement / acceptance-coupling problems of internal injection apply,
see P4 note): `L(A)=⋃L(Aᵢ) ⟹ ⋁ kr(Aᵢ) ≡ L(A)` and dually
`L(A)=⋂L(Aᵢ) ⟹ ⋀ kr(Aᵢ) ≡ L(A)`. `reconstruct_decomposed(aut)` (AUTOMATON-in —
the kr contract is an automaton/HOA, never an LTL formula) normalizes to a
DETERMINISTIC, STATE-MINIMAL GENERIC automaton, then dispatches on the
acceptance condition:
  - `_to_split_form`: `postprocess(aut,"deterministic","generic")` (keeps the
    conjunctive `⋀Inf`/Streett shape instead of collapsing to parity) THEN
    `sat_minimize` (gated `KR_SAT_MIN_STATES`, best-effort). State minimality is
    load-bearing: kr's census is acutely sensitive to the input state count (it
    sets cascade depth). `GFa&FGb`: `postprocess` alone leaves 2 states whose
    pieces explode (recombined tree 9.5e15); `sat_minimize` recovers the 1-state
    form (tree 313) — PURELY on the automaton, no formula (`probe_min_detgeneric`).
  - **AND by acceptance set** (`acc().get_acceptance().top_conjuncts()`): for a
    DETERMINISTIC automaton each word has one run, so `acc=⋀cᵢ ⟹ L=⋂L(A|cᵢ)`
    exactly; one single-condition sub-automaton per conjunct (clone via HOA
    round-trip, `set_acceptance`+`cleanup_acceptance_here`), recombine with `⋀`.
    Determinism is the precondition (nondet would give `⋂L(Aᵢ)⊋L(A)`).
  - **OR by strength** (`decompose_scc` weak/terminal/strong, Renault TACAS'13):
    union is the language for any automaton; recombine with `⋁`.
  - else single condition → existing monolithic kr (no regression, no gain).
Each piece runs the EXISTING `decompose_aut`+`reconstruct` (Fin web collapses to
a singleton good-set), so the Muller ∨/∧ is hoisted out of the Fin web to the
root — no hand-coding the §9.3 Σ/Π/Δ forms. Recurses depth-capped (a piece may
re-split by the other operator).

**It is now the survey's default path** (`survey_mp_cascade.py`, `KR_DECOMPOSE=1`
default; `=0` restores monolithic for A/B). Decompose-path survey
(`logs/survey_decompose_2026-06-13.txt`) vs the monolithic baseline
(`logs/survey_mp_cascade_2026-06-13.txt`): **0 of 8 two-level cases fail equiv,
zero regressions, and four acceptance-driven walls flip UNVERIFIED→True plus a
new 7-level case verifies**:

| case | split | monolithic verdict | decompose verdict |
|---|---|---|---|
| `GFa&GFb` | and(2) | UNVERIFIED 9.08×10¹⁶ | **True** (tree 111, 20 temporals) |
| `(aUb)\|Gc` | or(2) | UNVERIFIED 6.97M | **True** (637) |
| `(GFa&FGb)` | and(2) | UNVERIFIED 2⁶⁰ | **True** (reactivity) |
| `GFa->GFb` | and | (n/a) | **True** |
| `G(a->Fb)&G(c->Fd)` | and(2) | (new case) | **True** at L=7 |
| `Ga\|Fb` | or(2) | True (tree 499) | **True** (tree 21, 2 temporals) |
| `GFa&GFb&GFc` | and(3) | can't build (5M guard) | SPOT_TIMEOUT (30 temp, cap); compositional **SOUND** |

Verification at scale: for n≥3 the recombined `⋀` itself trips Spot's 32-acc cap,
so the sound witness is COMPOSITIONAL — `kr(pieceᵢ) ≡ L(pieceᵢ)` per single-Büchi
piece (small, cap-safe), which by `L(A)=⋂L(pieceᵢ)` gives `⋀kr(pieceᵢ) ≡ L(A)`
without translating the product (`probe_and_decompose.py`). Gates this revision:
r4_audit CLEAN; survey 8/0 both paths. Kept tools: `decompose_recombine.py`
(module), `test_decompose_recombine.py` (dispatch sweep), `probe_and_decompose.py`
(compositional verdicts). One-shot probes folded to git history, findings recorded
here: `probe_acc_split_api` (Spot acc-split API: `top_conjuncts()` on
`get_acceptance()`; clone via HOA round-trip — `make_twa_graph` single-arg absent
and `twa.prop_set` unexposed in system Spot 2.14.5) and `probe_min_detgeneric`
(automaton-only state minimization census — `sat_minimize` recovers the minimal
det-generic form where `postprocess` alone does not; `GFa&FGb` 2→1 state).
KNOWN LIMITATIONS (acceptance ABSORPTION blocks both splits): `GFa&Gb`
(recurrence ∧ safety) and `FGa|FGb` (persistence union) — Spot's determinization
folds the second component into a single acceptance set / strength, so the split
sees one piece (`none`) and the case stays at the monolithic wall (89-temporal /
2⁶⁰). The principled fix (expose the absorbed component as a separate
conjunct/strength) is blocked by that folding.
Scope: attacks the ACCEPTANCE-driven census (recurrence/persistence/mixed-strength
wall); orthogonal to the REACH/cascade-driven census (`G(a->Xb)`, `X(a&Xa)`,
`G(a->Xa)`, `F(a&Xb)` unchanged — one piece each, the P0 fold job).
Open: export from `kr/__init__.py` (separate commit); the absorption cases above.

## Tooling for targeted work

All under `kr/testing/` (placed scripts only; subprocess isolation; small
built-in budgets — a blown budget is a finding, not a nuisance).

**One-shot probe lifecycle (cleanup 2026-06-12):** a probe built to answer
ONE question is committed, its finding recorded here, then deleted — git
history keeps it. Removed in that sweep: `probe_object_translate` (finding
above), `probe_native_ops` (native-basis closure above), `probe_2l_rwith`,
`probe_sbacc` (sbacc is baked into the pipeline), `test_kr_arch_adopt`
(architecture adopted), `test_kr_muller` (Muller handling settled in
`config_graph`), `diag_stability` (per-case subprocess isolation is now
standard in every script). Dead code swept from the core the same day:
unused `_F`/`_G` sugar builders (outputs get native F/G via `_simp_f` NNF),
and the never-read legacy 7-tuple `_reach_memo` write in `reach_strong`
(`_reach_memo` itself stays — `fin.py` caches through it).
`kr/testing/logs/` holds committed baseline size censuses for before/after
comparison of fold work.

- `survey_mp_cascade.py` — MP-class × depth ladder; construction and
  Spot-equiv phases in separate subprocesses with separate budgets
  (`KR_CONSTRUCT_TIMEOUT` 30s / `KR_SPOT_EQUIV_TIMEOUT` 10s).
- `trace_fin_semantics.py` — per-config semantic grounding of fin_c sub-terms
  vs GTs on the config semiautomaton (cover-aware), witness words, per-check
  subprocess cap (`KR_CHECK_TIMEOUT`); verdicts OK/BAD/UNVERIFIED; prints
  truncated; >2MB sub-terms fast-skipped.
- `probe_reset_consistency.py` — soundness precondition: every combined letter
  acts identity-or-reset per level under both context conventions.
- `probe_sgpdec_api.g` — hand-run GAP ground truth for the SgpDec bridge calls
  (lift/π inversion, morphism property, closure).
- `probe_memo_stats.py` — memo profiler: distinct subproblems vs raw calls,
  helper-memo size, alarm + watchdog stack dump (names the native call when
  stuck in C++).
- `measure_formula_dag.py` — DAG vs string size of the assembled formula
  (now measuring the real reconstruct output); `--no-str` to measure cases
  whose flat form is 100MB+.
- `probe_tail_anatomy.py` — per-level dissection of the helper memo:
  subproblem counts by operator tag, DISTINCT tails/betas/(S,B,T) triples,
  tail-size quartiles, tail growth ratios. The tool that showed tails (not
  the avoid web) drive the explosion and measured the A-iteration.
- `probe_case_diff.py` — containment + witness for one full roundtrip,
  in-process build + fresh diff child via stdin (multi-MB formulas can't
  ride argv).
- `ltl_diff.py` — containment direction + witness words.
- `test_kr_r4_audit.py` — structural checklist + drift grounding (gate for
  operator commits).
- `test_kr_zoom.py` / `test_kr_reconstruct.py` — single-case full trace /
  multi-case roundtrip with isolated equiv.
