# Construction history (aut2ltl)

The dated, narrative record of how the construction reached its current state —
the "DONE / WIRED / LANDED / tried-and-reverted" log. **Not needed to start a
session** (read `aut2ltl/kr/STATUS.md` for current state; this file is the
archive). Moved out of STATUS.md on 2026-06-14 (P-ARCH step 11).

> Paths/module names below are AS-OF the time each entry was written (e.g.
> `kr/heuristic_gate.py`, `buchi2ltl/`, `kr/testing/`). The current layout is
> `aut2ltl/{kr,sl,portfolio,contract,cli}` with tests under `tests/`. The
> findings stand; translate paths through the P-ARCH move (git log / STATUS).

## Folding & simplification passes (2026-06-12)

- **Letter fusion (the "B" iteration — dag_folding.md counter-measure B, default
  ON, `KR_FUSE_LETTERS=0` restores the per-letter literal shape).** At every
  enumeration site (solid⁺/wsolid⁺ last-step/leave/bad-pre, dashed
  enter_t/enter_b/line-3, fin's `_uncond_reach_strict`) the summand reads the
  letter only through its guard, so letters are grouped by the `_dedupe` key minus
  `li` (enter sites key on the arrival too) and each group emits ONE summand whose
  guard is the Minato-minimized OR (`_fuse_or` in ltl_builders: BDD round-trip via
  `spot.formula_to_bdd`/`bdd_to_formula`, process-lifetime bdd_dict, plain-Or
  fallback). One tail per outcome class instead of per letter — the distinct-tail
  driver shrinks at the source. Soundness argument: dag_folding.md "Letter fusion".
  Measured: `XXa`/`XXXa` collapse to the LITERAL formulas (3/4 tree nodes; XXXa was
  SPOT_TIMEOUT); `Xa` output is `Xa`; `G(a->Xb)` tree 3.6M→22.6k and distinct
  temporal 226→85 (under the 32-acc-set cap → equiv=True); `G(p->(qUr))` tree
  84.8M→55k, 559→121; `G(a->Xa)` 5.1×10¹¹→11.3M; `(a U b)|Gc` 2⁶⁰-saturated→528M;
  `X(a&Xa)` 6.3×10¹³→3.1×10¹⁰ (the remaining ladder wall). Survey: 3 cases flipped
  to True (`XXXa`, `G(a->Xb)`, `Ga|Gb`), zero regressions; grounding: zero
  contradictions; audit CLEAN. Post-fusion log: `kr/testing/logs/fusion_measure_dag_*`.

- **Own rewrite pass wired (the "1c" iteration — kr/simplify/ package,
  KR_SIMP_OWN=1 default, size cap KR_SIMP_OWN_LIMIT=2000, KR_SIMP_OWN_FACTOR toggles
  rule 3).** Three rules Spot lacks (validated standalone 44/44 + 1500-formula
  random fuzz ALL EQUIVALENT, oracle self-tested): (1) context pass —
  sibling-context propagation over the boolean skeleton, identity domination incl.
  temporal nodes, Shannon at Or, reset at temporal boundaries; (2) now-evaluation —
  one-step unroll of G/F/U/R/W/M heads under boolean context (initial-state
  knowledge, Bonneland et al. lineage), two-tier entailment (identity + BDD);
  (3) sound partial factoring + Minato guard groups. Hooked per node in `_simp_f`
  after Spot's pass (one bounded Spot re-pass when rules fire); persistent package
  memos make it amortized O(1) per distinct node; ONE shared bdd_dict per process (a
  second dict next to the fusion one corrupted the equiv-child heap). The size cap
  exists because the uncapped pass sent 3 reactivity cases CONSTRUCT_TIMEOUT —
  capped, all construction times are healthy. Measured (capped, vs post-fusion):
  `Ga`→`a & G(!a|Xa)`, `Fa`→`a | F(!a&Xa)`, `a&Xa`→literal `a & Xa`; `G(a->Xb)` tree
  22.6k→12.2k; `G(p->(qUr))` 55k→38.7k; `G(a->Xa)` 11.3M→2.0M; `(aUb)|Gc` 528M→7.7M;
  giants barely move under the cap (`X(a&Xa)` 31G→27.9G). Survey 24 True / 0 FALSE;
  audit CLEAN; grounding zero contradictions. KNOWN regression: rewriting creates
  temporal-body VARIANTS that coexist across branches, raising the
  distinct-eventuality census — `F(a&Xb)` went back over the 32-acc cap (its equiv
  child then dies in the abort path's teardown: `free(): invalid pointer` — infra,
  not semantic). Refinement item: eventuality-aware rewriting (TODO 1c).

- **Unroll-inverse fold pass (the "rule 4" iteration — kr/simplify/fold_pass.py,
  KR_SIMP_OWN_FOLD=1 default).** Eight pair-folds (expansion laws backwards,
  arbitrary subformulas): `c|XFc→Fc`, `c&XGc→Gc`, U/W/R/M one-step forms,
  first-occurrence `c|F(¬c&Xc)→Fc`, induction `c&G(¬c|Xc)→Gc`; plus S1/S2 sibling
  subsumption (Formula-5 line redundancy): `c|X(cRd)|G(c|Xd)→c|X(cRd)` and dual
  `c&X(cUd)&F(c&Xd)→c&X(cUd)` (proofs in module docstring; M/W variants UNSOUND,
  regression-tested; the one-step-SHIFTED ladder variants are genuinely not
  redundant — witness `!a; a; cycle{!a}`). Validated: test_fold_pass 26/26, all
  suites CLEAN, fuzz 3×500 ALL EQUIVALENT zero growth, audit CLEAN. Measured (vs
  post-1c): `F(a&Xa)` census 55→33 / tree 4611→901 / DAG 269→156; `F(a&Xb)` 109→87;
  `G(a|Xb)` 94→82; `G(a->Xa)` 193→147, tree 2.0M→1.5M. Survey: **`G(a->Xb)` flipped
  SPOT_TIMEOUT→True (25 True / 0 FALSE)**, `(aUb)|Gc` 7.7M→6.6M, `X(a&Xa)`
  flatten-gate census 23.1G→13.3G (NB measure_formula_dag's unfolded count for that
  case moved 52.6M→127M — fold changes memo keys and thus the construction path; DAG
  and temporal census both improved). Diagnosis tool: `kr/testing/probe_dag_dump.py`
  (let-binding DAG view + temporal census; the F(a&Xa) dumps that drove the rules are
  in `kr/testing/logs/faxa_dag_dump*.txt`).

- **Per-DAG-node memoized simplification (the "A" iteration).** `_simp_f`
  simplifies each hash-consed node ONCE (id-keyed memo + the shared tl_simplifier's
  internal cache); operators build bottom-up so every call sees already-simplified
  children. Policy `KR_SIMP_OPTS`: hybrid (default) = Spot's full rules only on nodes
  with unfolded size ≤ `KR_SIMP_FULL_LIMIT` (2000), basics (constant folding, X(0)→0)
  above — full's syntactic-implication pass is pairwise and sharing-blind and stalled
  >15s per-node on `X(a&Xa)`, basics never stalls. `KR_SIMP_NODE=0` = old identity
  behavior. Paired with the dead-tail early-out in reach_strong (`reach(…,τ≡false) ≡
  false`, the Table-1 base case), folded tails delete their memo-key subtrees.
  Measured: `a&Xa` 752→311 subproblems; `G(a->Xb)` distinct temporal 538→226,
  unfolded tree 85.5M→3.6M; `G(p->(qUr))` distinct temporal 4115→559 (7.4x); `X(a&Xa)`
  max tail 177x smaller (counts −20% only — the residual is genuine b^k wrapping, see
  dag_folding.md). We still never WAIT on Spot: each call is one node with simplified
  children, and the escape hatch drops Spot from the path entirely.

## Census reduction (2026-06-13)

- **Initial-state opening + context-aware subsumption.** Three additions on top of
  rule 4. (i) Context OPENING (context_pass): temporal siblings feed their
  now-component into the context — Gφ asserts conj(φ), R/M assert conj(g); at Or, Fφ
  refutes disj(φ), U/W refute disj(g). Opened facts flow ONE-WAY (earlier→later in
  canonical child order): bidirectional opening built circular support and was caught
  UNSOUND by fuzz (witness `!(b R (Gb & (b M Gb)))` → 0; the opened b erased the
  sibling b while the M consumed it) — one-way is sound by sequential replacement;
  regression cases in test_context_pass. (ii) G/F ABSORPTION (fold_pass): conjuncts
  implied by a sibling Gφ dropped (small recursive entailment: X/F/G bodies, U/M arms,
  And/Or), dual at Or. (iii) **Context-aware S1/S2** (fold_pass.ctx_subsume, hooked as
  bool_hook into the context pass): under ctx ⊨ ¬c the S1 bare-c case is discharged by
  knowledge, so the unshifted AND the one-step-SHIFTED ladder forms fold — the shapes
  that are provably NOT redundant in isolation. **This pushed `F(a&Xa)` under the
  32-acc cap: census 33→26, Spot equiv True end-to-end.** Measured: `F(a&Xa)` DAG
  156→111, tree 901→453; `F(a&Xb)` census 87→74; `G(a|Xb)` 82→79, tree 6.8k→3.1k;
  survey `X(a&Xa)` flatten census 13.3G→1.5G. Gates: suites 19/18/10/38 CLEAN, fuzz
  3×500 ALL EQUIVALENT, audit CLEAN, survey 25 True / 0 FALSE. Known limitation:
  one-way flow + canonical order misses openings whose source sorts after the target
  (alternating direction across the pipeline's repeated context passes would be sound —
  TODO).

- **Census anatomy + arm-padding removal.** Two probes answered "where does the
  residual census live?" conclusively (`probe_census_classes`, `probe_muller_overlap`
  — both committed): (i) the post-rules census is ~all genuinely distinct languages
  (F(a&Xa) 26/26 classes, F(a&Xb) 74→73, G(a->Xa) 144→≤126), so formula-level interning
  has little headroom; (ii) the Muller DNF is NOT the driver — disjuncts share 83% of
  the census via hash-consing (G(p->(qUr)): two disjuncts, 77 census each, overlap 70,
  whole 84); (iii) **the Fin(C)/¬Fin terms ARE the driver**: per disjunct the two Fin
  conjuncts carry census ~50 each (DAG ~285 each) while the reach/invariant part is ~25
  — including a census-1 conjunct that is LITERALLY language-equivalent to the target
  body (`p -> (q U r)` verified): the construction contains the small answer, buried
  under the Muller-acceptance scaffolding. This is the evidence base for P1 (direct
  Σ₁/Π₁/Π₂/Σ₂ acceptance dispatch instead of the Muller DNF). Spin-off rule from the
  class probe (fold_pass, validated 42/42 + fuzz): **U/W/R arm-padding removal** —
  `(c & Xd) U g → c U g` when c ⇒ d and g ⇒ d (the Xd is implied by the U dynamics; dual
  for R; propositional-fragment entailment, sound one-way): G(p->(qUr)) census 98→84. NB
  the formula must be written `q U r` WITH SPACES — `qUr` parses as ONE atomic
  proposition (an earlier "solved at 21 nodes" reading of this case was that artifact).

- **Config-graph reach FALSE-cut: tried, NEGATIVE, reverted.** Hypothesis: prune
  `reach_strong(S,·,·,T,·)` to `false` when the target is graph-unreachable from the
  source in the config automaton — a cheap, exact, Spot-free cut at the source of the
  σ∧Xτ ladder. Two corrections shrank it to nothing. (1) Soundness: the paper's avoid
  is β-guarded and STRICT-BEFORE arrival (`∀j∈[0..i). δ≠B ∨ w⊭β`, Automata2LTL.txt:573),
  so `T==B` does NOT imply false and walling B in the BFS is unsound — only avoid-FREE
  target reachability is sound. (2) The cut must be SUFFIX-projected, not full-config:
  at recursion level k the target is matched on `T[k:]` (the `level==n` base is `(¬β)Uτ`,
  dropping T), so a full-config cut is the k=0 case and is unsound at k>0. A read-only
  probe over the helper memo showed 30% "cuttable" full-config — but ~all of that was the
  unsound over-cut; the sound suffix-projected cut fires ~104×/41584 on `Xa & XXa` and
  changes DAG/tree/temporal census by ZERO, likewise zero on
  `G(a->Xb)`/`G(p->(qUr))`/`F(a&Xb)`/`Ga|Gb` (audit CLEAN, all equiv True throughout).
  Diagnosis, consistent with the census-anatomy finding above: the explosion lives in the
  **Fin(C) acceptance scaffolding, not in reach** — its redundancy is β/τ-obligation-driven,
  invisible to graph reachability. The free-tail collapse the user is after needs a
  Fin(C)-level recognizer (config in an absorbing accepting class ⇒ constant Fin term), not
  a reach cut. All code reverted; finding kept here.

- **Per-conjunct Fin-reachability fold: LANDED (the Fin(C)-level recognizer the bullet
  above asks for — generalizes and replaces the absorbing-M fold).**
  `config_graph.configs_reachable_from(casc, M)` (delegated via `Cascade`, consumed in
  `reconstruct_ltl_paper_style`; default on, `KR_FOLD_FIN_REACH=0` restores the full
  Muller term). For a good Muller set M, keep `Fin(C∉M)` **only for C reachable from M**
  in the config graph; drop it for every C off M's forward cone. Soundness (per term):
  the `¬Fin(C∈M)` conjuncts force Inf⊇M, and the i.o.-set of a path in a finite digraph
  is **strongly connected**, so any C∈Inf is reachable from M within Inf; contrapositive,
  C unreachable from M ⟹ C∉Inf ⟹ `Fin(C)` — implied, droppable. Pure graph property, no
  containment check. **Subsumes the absorbing-M fold** (M absorbing ⟺ reach(M)=M ⟹ all
  `Fin(C∉M)` drop) and fires where absorbing did not (non-bottom M with a side/transient C
  off its cone). Two wins: (i) it prunes more conjuncts AND (ii) the kept-config set is
  decided BEFORE building `fin_c` — the explosive part — so dropped configs cost zero
  construction. **It bites the distinct-temporal census (the 32-acc driver), not just the
  unfolded tree** — unlike absorbing-only. Measured, no-fold→per-conjunct (absorbing-only
  in parens), `logs/survey_sizes_perconj_2026-06-13`: `a U b` tree 87→13 / temporals 4→1 →
  the LITERAL `b | ((a&!b) U (a&!b&Xb))`; **`F(a&Xb)` tree 4251→2739 / temporals 74→64
  (absorbing: 74, no change)**; `(aUb)|Gc` 637→525 / 22→18 (abs 19); `Ga|Gb` 7026→6438 /
  47→46 (abs: no change); `Fa&Gb` 187→159 / 12→11 (abs: no change); `G(a->Xa)` 144→141;
  `X(a&Xa)` 4138→4134. Still over the cap where they were (`F(a&Xb)` 64>32), but the census
  is now moving on reach-driven cases. Audit CLEAN; survey 0 fail / no regressions. Open:
  the cap cases need deeper census reduction (the kept `¬Fin(M)` / reachable-`Fin` part
  still dominates — census-anatomy finding).

## Acceptance dispatch — direct hierarchy-class φ per Theorem 2 / §9.3 (2026-06-13)

- **Büchi class WIRED on the default path. The structural fix the census-anatomy finding
  pointed to.** `kr/acceptance_dispatch.py` `reconstruct_buchi(casc)`: a deterministic
  **Büchi** cascade (`acc=Inf(0)`, `Π₂`) gets the DIRECT form `φ := ⋁_{C∈α} ¬Fin(C)` — NO
  `Fin(C∉G)` web and NO good-set enumeration (the two Muller-DNF explosions). Soundness:
  `¬Fin(C)` ≡ "C∈inf-set"; the inf-set is strongly connected, so Büchi `inf∩α≠∅` ≡
  `⋁_{C∈α}¬Fin(C)` (a transient accepting C ⇒ `¬Fin`≡false, harmless).
  - **Wiring:** a TOP-LEVEL pre-check at the head of `reconstruct_ltl_paper_style` (gate
    `KR_DISPATCH_BUCHI`, default ON; `=0` restores pure Muller for A/B). The hook lives
    THERE — not in `reconstruct_bls` — because the GOTO decompose front end
    (`reconstruct_decomposed`) calls `reconstruct_ltl_paper_style` directly per piece; the
    single pre-check covers BOTH entries. Single-condition decompose pieces are exactly
    Büchi/coBüchi, so the dispatch fires per piece (e.g. `GFa&GFb&GFc` and(3): each conjunct
    dispatches).
  - **α is COVER-AWARE** (`config_graph.buchi_accepting_configs`, delegated via `Cascade`):
    read off `build_pruned_config_aut` — every reachable config whose lifted (sbacc) marks
    satisfy the same `g.acc()` oracle `accepting_sc_subsets` uses — NOT the lift-section
    `accepting_configs()` (one config per state). The lift section UNDER-approximates on a
    genuine holonomy cover: wiring first flipped `F(a&Xb)` to equiv=FALSE (`L(buchi)⊊L(orig)`,
    α missed the duplicated accepting sink), the cover reader gives the exact α={(1,1),(1,2)}.
  - **Results (size A/B on the decompose path, `logs/sizes_dispatch_{on,off}_2026-06-13`):**
    `G(p->(qUr))` 84→**14** (tree 20291→751, UNDER the cap → survey equiv=True — the
    challenge case); `G(a->Xa)` 141→30 (tree 1.53M→703); `G(a->Xb)` 79→23; `F(a&Xb)` 64→40;
    `Ga|Gb` 46→18; `GFa` 10→3; `GFa&GFb` 20→6; `GFa&GFb&GFc` 30→9; `X(a&Xa)` 4134→2069 (still
    over the flatten gate — reach-driven). Totals over 35 cases: DAG 61029→47498 (−22%),
    distinct temporals 10907→8491 (−22%); excluding the two giants the tractable cases drop
    578→227 (−61%). **Survey (`logs/survey_wire_buchi_2026-06-13`): 0/35 equiv=FALSE, four
    walls flipped True (`G(p->(qUr))`, `F(a&Xb)`, `G(a->Xa)`, `GFa&GFb&GFc`), zero
    regressions; audit CLEAN.**

- **coBüchi class WIRED, the mirror of Büchi.** `reconstruct_cobuchi(casc)`: a deterministic
  **coBüchi** (persistence, `Σ₂`) cascade gets `φ := ⋀_{C∈α} Fin(C)` (α = the "visit
  finitely"/marked configs) — exact, since coBüchi acceptance is `Inf(ρ)∩Marked=∅` ≡
  `⋀ Fin(C)` (a transient marked C ⇒ `Fin`≡true, harmless). Wired as a SECOND pre-check after
  Büchi in `reconstruct_ltl_paper_style` (gate `KR_DISPATCH_COBUCHI`, default ON). α =
  `config_graph.cobuchi_finite_configs` — the cover-aware DUAL of the Büchi reader. **GATE
  SUBTLETY (the crux, found UNDER decomposition):** `decompose_aut`'s parity step turns the
  natural `Fin(0)` into `Inf(0)|Fin(1)`, on which `acc().is_co_buchi()` is False; the gate
  recovers the natural acceptance via `postprocess(.,"deterministic","generic")` and tests
  `is_co_buchi` there. The `postprocess(.,"coBuchi")` variant is UNSOUND — a recurrence
  cascade (`GFa`) passes it. **Results (`logs/sizes_dispatch_cobuchi_2026-06-13`):** `FGa`
  6→3 temporals, `F(a&Gb)` 7→4, `FGa|FGb` **6195→2779** (tree 1.15×10¹⁸→3.23×10¹⁷ — census
  >½ off, still over the flatten gate so UNVERIFIED, the residual is reach-driven), and the
  reactivity `(GFa&FGb)` 10→7 (its `FGb` AND-piece dispatches). Totals over 35 cases DAG
  47498→28207, distinct temporals 8491→5066 (both −40%). Survey
  (`logs/survey_wire_cobuchi_2026-06-13`): 0/35 equiv=FALSE; audit CLEAN.

- **weak/looping (Δ₁/Σ₁/Π₁) WIRED but OFF by default (`KR_DISPATCH_WEAK`, the experimental
  A/B baseline).** `reconstruct_weak(casc)` = `⋁ over accepting SCC G : end_in(G)`, with
  `end_in(G) = (⋁_{C∈H} reach_to(ι,C)) ∧ (⋀_{C'∈G'} ¬reach_to(ι,C'))` — pure `reach_to`
  (`reach_strong(ι,C,⊥,C,⊤)`), NO Fin; subsumes looping-Büchi (safety `⋀¬reach_to(sink)`) and
  looping-coBüchi (guarantee `⋁reach_to(sink)`). Gate `is_weak_cascade` =
  `is_weak_automaton(postprocess(.,"generic"))`. Placed BEFORE Büchi/coBüchi. Correct
  (flag-on survey 0/35 equiv=FALSE) but a SIZE REGRESSION and therefore kept OFF —
  `probe_weak_dispatch` / `probe_looping_dispatch`: the general form is worse on 6/7 cases;
  dedicated looping is mixed (2 wins `Ga|Gb` 18→14, `F(a&Xb)` 40→30; 3 losses `G(a->Xa)` tree
  703→6263, `G(a->Xb)` 23→30, `a U b` 1→3). Root cause: weak languages are already handled
  smaller by Büchi/coBüchi, and the residual is **reach-driven** (the τ-tail), which NO
  acceptance form touches. Kept in (flagged off) as the A/B baseline for `Acc(c)`.

- **Config-indexed `Acc(c)` for the BOUNDED fragment — WIRED, default ON. Cracks the
  `X(a&Xa)` reach wall: UNVERIFIED 5.1×10⁸ → equiv=True, literal output.**
  `reconstruct_acc(casc)` (`KR_DISPATCH_ACC`, default ON, FIRST in the dispatch chain).
  `φ := Acc(ι)` by bounded unroll of the config graph: `Acc(c) = ⊤` if `L(D from state_of(c))`
  is universal, `⊥` if empty (R1, a small Spot ⊤/⊥ oracle on the INPUT automaton D — lazy +
  cached, NOT on the output); else `⋁_σ guard(σ) ∧ X Acc(move_config(c,σ))` (R2 unroll).
  **SELF-GATING:** a config re-entered on the unroll path that is not ⊤/⊥ is recurrent ⇒ Acc
  declines (None ⇒ caller falls back to the Büchi/coBüchi/Muller chain), so it fires only on
  the bottom/bounded class. It bypasses the reach machinery entirely (no reach_to, no Fin, no
  τ-tail), emitting the literal formula. Complexity `O(|reachable configs| × |Σ|)` memoized
  builds plus ≤ n bounded oracle calls on the small `D`. Measured (`probe_acc_dispatch`):
  `X(a&Xa)` BLS 11835/5.1×10⁸/2069 → Acc **4/5/0**, equiv True; the whole X-ladder collapses
  to the literal; every recurrent control declines → BLS. **Survey
  (`logs/survey_wire_acc_2026-06-13`): the ONLY verdict change is `X(a&Xa)` UNVERIFIED→True;
  0/35 FALSE, zero regressions; audit CLEAN.** Scope (`probe_acc_fuzz`, 3×60 randltl): gate
  rate ~24% but fired cases are almost all TRIVIAL; the high-value deep-bounded case is a rare
  tail. Kept ON (cheap, self-declining, only thing that reaches the bounded reach wall).
  Caveat: Spot ⊤/⊥ oracle in the construction path (bounded, small input) — a structural
  sink-reachability test could replace it (TODO).

## Decompose-and-recombine at the root — LANDED + made the GOTO path (2026-06-13)

`kr/decompose_recombine.py` (orthogonal module, core untouched). ROOT-level language
operations recombine kr outputs soundly with no caveats (kr is language-faithful, a root
operator is a pure position-0 language op): `L(A)=⋃L(Aᵢ) ⟹ ⋁ kr(Aᵢ) ≡ L(A)` and dually
`L(A)=⋂L(Aᵢ) ⟹ ⋀ kr(Aᵢ) ≡ L(A)`. `reconstruct_decomposed(aut)` (AUTOMATON-in) normalizes to
a DETERMINISTIC, STATE-MINIMAL GENERIC automaton, then dispatches:
- `_to_split_form`: `postprocess(aut,"deterministic","generic")` (keeps the conjunctive
  `⋀Inf`/Streett shape) THEN `sat_minimize` (gated `KR_SAT_MIN_STATES`). State minimality is
  load-bearing: kr's census is acutely sensitive to the input state count. `GFa&FGb`:
  `postprocess` alone leaves 2 states whose pieces explode (recombined tree 9.5e15);
  `sat_minimize` recovers the 1-state form (tree 313) — PURELY on the automaton
  (`probe_min_detgeneric`).
- **AND by acceptance set** (`acc().get_acceptance().top_conjuncts()`): for a DETERMINISTIC
  automaton each word has one run, so `acc=⋀cᵢ ⟹ L=⋂L(A|cᵢ)` exactly; one single-condition
  sub-automaton per conjunct (clone via HOA round-trip), recombine with `⋀`.
- **OR by strength** (`decompose_scc` weak/terminal/strong, Renault TACAS'13): union is the
  language; recombine with `⋁`.
- else single condition → existing monolithic kr.
Each piece runs the EXISTING `decompose_aut`+`reconstruct` (Fin web collapses to a singleton
good-set), so the Muller ∨/∧ is hoisted out of the Fin web to the root — no hand-coding the
§9.3 Σ/Π/Δ forms. Decompose-path survey (`logs/survey_decompose_2026-06-13.txt`) vs the
monolithic baseline: **0 of 8 two-level cases fail equiv, zero regressions, four
acceptance-driven walls flip UNVERIFIED→True plus a new 7-level case verifies**:

| case | split | monolithic | decompose |
|---|---|---|---|
| `GFa&GFb` | and(2) | UNVERIFIED 9.08×10¹⁶ | **True** (tree 111, 20 temporals) |
| `(aUb)\|Gc` | or(2) | UNVERIFIED 6.97M | **True** (637) |
| `(GFa&FGb)` | and(2) | UNVERIFIED 2⁶⁰ | **True** |
| `GFa->GFb` | and | (n/a) | **True** |
| `G(a->Fb)&G(c->Fd)` | and(2) | (new) | **True** at L=7 |
| `Ga\|Fb` | or(2) | True (tree 499) | **True** (tree 21, 2 temporals) |
| `GFa&GFb&GFc` | and(3) | can't build | SPOT_TIMEOUT (cap); compositional **SOUND** |

Verification at scale: for n≥3 the recombined `⋀` trips Spot's 32-acc cap, so the sound
witness is COMPOSITIONAL — `kr(pieceᵢ) ≡ L(pieceᵢ)` per single-Büchi piece, which by
`L(A)=⋂L(pieceᵢ)` gives `⋀kr(pieceᵢ) ≡ L(A)` without translating the product
(`probe_and_decompose.py`). KNOWN LIMITATIONS (acceptance ABSORPTION blocks both splits):
`GFa&Gb` (recurrence ∧ safety) and `FGa|FGb` (persistence union) — Spot's determinization
folds the second component into a single acceptance set / strength, so the split sees one
piece (`none`). The principled fix (expose the absorbed component) is blocked by that folding
— since carried by the buchi2ltl gate (below).

## buchi2ltl heuristic gate + portfolio (2026-06-14)

- **buchi2ltl heuristic gate — WIRED into the decompose dispatcher, default ON. Cracks the
  last MP wall `FGa|FGb`; the MP survey is now a clean sweep.** `kr/heuristic_gate.py`
  `try_heuristic_gate(aut)` is the SINGLE seam between the two paths (the kr core operators
  import nothing from `buchi2ltl/`; the old "never mix" rule is retired). **Gate goes UNDER
  decomposition (`KR_GATE_UNDER_DECOMP`, default ON):** `decompose_recombine` splits FIRST and
  applies the gate only to the leaves that no longer split — so a decomposable input is always
  cut into pieces, even when the gate could take the whole. Exception: when the ROOT does not
  split, the gate runs on the RAW (pre-determinization) input. This makes the reported
  technique honest: a case `split_report` says `or(2)` now actually decomposes (`tech=or+sl`).
  Size effect is a wash (DAG 494→491, temporal 114→119).
  - **Soundness is a composition of sound steps, NO per-call equiv check:** arbitrary HOA
    →(Spot `postprocess` to TGBA, language-preserving)→ buchi2ltl. buchi2ltl's CORE is `sl`
    (self-loop backward labeling) — an EXACT state-elimination translation on the very-weak
    (1-weak) fragment, DECLINING (`UNSUPPORTED`) elsewhere; its f2/t2 layer is a separate
    verify-before-use guess-and-check. So adopted output is sound by construction. The bounded
    equiv check is an OPT-IN audit (`KR_GATE_VERIFY`, default OFF). **Audited at scale
    (`fuzz_gate_decompose.py`, VERIFY=1, 3 seeds ≈170 randltl / 191 piece-adoptions): 0
    equiv=FALSE, 0 rejections, ~81% adopt rate** (`logs/fuzz_gate_seed{1,2,3}_2026-06-14`).
  - **Why determinize-then-gate is NOT enough (`probe_gate_redet.py`):** buchi2ltl's backward
    labeling exploits the (often nondeterministic) translate-style TGBA, which
    `_to_split_form`'s determinization destroys. `FGa|FGb` goes raw 3-state nondet Büchi
    (buchi2ltl ok tree=13) → det 2-state coBüchi → re-projected 4-state nondet Büchi that
    buchi2ltl DECLINES — a one-way loss. Hence the gate runs on the RAW input exactly when the
    root does not split.
  - **Adopted output is simplified through `_simp_f`** (buchi2ltl does not wire Spot's LTL
    simplifier; `Fa|Gb` raw 5-temporal → 2-temporal). `probe_gate_inspect.py` shows
    before/after.
  - **Results (gate ON vs OFF, `logs/survey_sizes_gate_{on,off}_2026-06-14`):** `FGa|FGb`
    **2779→3** (tree 3.2×10¹⁷→6 — the last wall collapses); `G(a->Xb)` 23→1; `G(a->Xa)` 30→2;
    `Ga|Gb` 18→3; `GFa->GFb` 19→4; `GFa&GFb&GFc` tree 46→8 / 9→4; `(aUb)|Gc` 9→3; `Fa&Gb` 7→2.
    Totals over 35 cases: distinct temporals **2997→114 (−96%)**, DAG 16376→494, tree
    3.2×10¹⁷→1951. **Zero regressions.**
  - **Gates:** r4 audit CLEAN; MP survey `logs/survey_gate_buchi2ltl_2026-06-14` **0/35
    equiv=FALSE, every case True**. Gate `KR_GATE_BUCHI2LTL` (default ON). Side-by-side:
    `testing/run_mp_through_buchi2ltl.py` (30/35 handled standalone, 0 FALSE).

- **Portfolio result struct (`kr.recon_result.ReconResult`).** kr is now a portfolio (gate /
  and-split / or-split / acc / weak / buchi / cobuchi / bls-Muller), so `reconstruct_decomposed`
  returns a `ReconResult` (`.formula` + `.technique`, a deduped SET of method tags) instead of a
  bare formula. buchi2ltl's `reconstruct_ltl` returns the SAME struct. The set is threaded by
  reference down the dispatch (MT-safe). Wired into both surveys' `tech=` column.

- **Contract reification — `status` (P-ARCH step 1).** `ReconResult` gained an explicit
  `status` (OK / DECLINED) with `ReconResult.decline()` / `.declined` / `.ok`; "not me" is no
  longer the `UNSUPPORTED` string smuggled inside `.formula` (engines still use that string
  INTERNALLY in their recursion — translated to DECLINED at the boundary return of
  `reconstruct_ltl`). Consumers branch on `.declined`. The `Translator` Protocol (callable
  `twa -> ReconResult`; invariant: language-faithful OR declines, never wrong) is documented in
  the contract module. Gates: r4 audit CLEAN, MP survey clean sweep
  (`logs/survey_parch_step1_2026-06-14.txt`).

- **kr UNDER sl — full-suffix delegation prototype (`kr/sl_driven.py` + one optional
  `buchi2ltl` hook). The mirror of the decompose gate.** `reconstruct_sl_driven(aut)` runs sl
  as the DRIVER; at any multi-state-SCC state it delegates the whole sub-automaton A_q to the
  normal `reconstruct_decomposed` and reattaches the label. Seam: optional `scc_labeler`
  callback on the DAG-native engine `reconstruct_ltl` (the labeler returns a `spot.formula` DAG,
  spliced as a child node WITHOUT flattening). Termination: delegated kr uses the sl GATE (no
  labeler) → declines the core → cascade; never re-enters the driver. Soundness: the delegated
  label is L(A_q) = exactly the language sl's own label(q) represents (`probe_sl_compose`: 0
  equiv=FALSE). Results: `XX(G(a->Fb))` kr-on-full 5596 DAG / **1.2×10¹⁴ tree** → sl-driven
  **21 nodes**; `c U (G(a->Fb))` kr-on-full TIMEOUT → **28**; `XX(F(a&Xb))` 2957 DAG / 1.1×10⁹
  tree → 183. **Boundary flattening RESOLVED (buchi2ltl is now DAG-native):** `reconstruct_ltl`
  builds a hash-consed `spot.formula` DAG end to end (t2 fragments included); the `scc_labeler`
  returns the kr DAG directly (no `str()`). The DAG engine was cross-oracled against the (now
  deleted) string engine across the MP ladder + randltl with 0 divergences. Not wired into any
  default path (a top-level chooser + scale soundness fuzz are later steps).

## Representation / verification probes (dead ends, kept as record)

- **Object-out API landed (P0 plumbing, 2026-06-12).** With reconstruct returning the DAG and
  harnesses flattening only under `KR_FLATTEN_TREE_LIMIT` (survey default 5M tree nodes), the
  former CONSTRUCT_TIMEOUT class became measured verdicts in seconds: `G(a->Xa)` ~2k DAG nodes
  unfolding to **5.1×10¹¹** tree nodes (sharing ~2.5×10⁸); `(a U b)|Gc` saturates the counter at
  2⁶⁰. Audit CLEAN.

- **Native-operator basis: investigated and CLOSED (2026-06-12, `probe_native_ops`).** Spot's
  constructors do NOT rewrite sugar (`U(1,a)` and `¬(a U b)` stay raw nodes), but the per-node
  simplifier normalizes every node to NNF even in basics-only mode; since the operators build
  bottom-up through `_simp_f`, **outputs are already in the native G/F/R/W basis** — census of
  real outputs shows `Not` only over atomic propositions. The surviving U nodes are GENUINE
  strong eventualities (distinct `¬β U τ` base cases): 94 in `G(a->Xb)`, 246 in `G(p->(qUr))` —
  the >32-acc-set driver is the genuine eventuality count, which no operator-basis change can
  reduce. Reduction must come from folding or non-translation verification. Baselines:
  `kr/testing/logs/baseline_*_2026-06-12.txt`.

- **Object-path translation is a dead end (2026-06-12, `probe_object_translate.py`).** Spot
  accepts our formula objects natively (`ltl_to_tgba_fm`, `translate`, `translator` class — no
  string round-trip), but Couvreur allocates one acceptance set per DISTINCT eventuality: our
  400–600 distinct temporal subterms blow the compile-time `mark_t` cap (32 in system Spot
  2.14.5) instantly, and `Ga|Gb` grinds >10s in the tableau before reaching the cap — the
  tableau's state space is sets of subformulas, which hash-consing does not shrink. Verification
  must come from word sampling / compositional grounding, or from folding the eventuality count
  below the cap.

## One-shot probe lifecycle (cleanup 2026-06-12)

A probe built to answer ONE question is committed, its finding recorded, then deleted — git
history keeps it. Removed in that sweep: `probe_object_translate`, `probe_native_ops`,
`probe_2l_rwith`, `probe_sbacc` (sbacc is baked into the pipeline), `test_kr_arch_adopt`,
`test_kr_muller` (settled in `config_graph`), `diag_stability` (per-case subprocess isolation
is now standard). Dead code swept the same day: unused `_F`/`_G` sugar builders (outputs get
native F/G via `_simp_f` NNF), and the never-read legacy 7-tuple `_reach_memo` write in
`reach_strong` (`_reach_memo` itself stays — `fin.py` caches through it).

## sl_driven full-suffix delegation — invariant-strip soundness fix (2026-06-15)

Kinská counting cases 06/07/09/10 reconstructed to unsound under-approximations
(06: L = (a.!a)*.a^w came out as bare `a`). Root cause: `reconstruct_ltl` strips
each state's downstream invariant off the automaton
(`_apply_downstream_invariants`), sound only because the linear walk re-adds it,
timed (X-wrapped), as it ENTERS the owning state. Full-suffix delegation skips
that walk; when the init state is itself in a multi-state SCC, `label(init)`
delegates the whole automaton up front, so a stripped INTERIOR invariant (a
terminal sink's `G a`) is never re-added and the delegate translates a widened
language. Not a loop-back/prefix issue (the sink is terminal) and not fixable by
a single end-AND (the invariant is interior, not global to the suffix, so it has
a temporal moment lost in the opaque fragment). Fix: keep `pristine_aut`
(pre-strip) and root `_sub_automaton_from` on it — numbering is preserved, the
delegate sees the invariant intact. 06/07 -> sound UNVERIFIED_SIZE; 09/10 ->
correctly NOT_LTL (the bogus `a` had masked the aperiodicity gate). Full kinska
sweep FALSE 4 -> 0. Tools kept: tests/sl/trace_sl_driven.py,
tests/sl/init_scc_report.py, tests/kr/diff_hoa.py, tests/kinska_breakdown.py.

Harness, same day: tests/survey.py enforces the per-case budget via
`timeout --signal=INT --kill-after=1` so a runaway GAP is reaped (no orphan), and
reports external wall time as build_s for every outcome. tests/kinska_sweep.sh
sweeps the corpus at a strict 15s/run (prunes its own logs/ from discovery).

## 2026-06-15 — simplify rule 4: boolean left-arm cofactoring (DONE)

New rule in `aut2ltl/ltl/simplify` (fold_pass `_arm_cofactor`, helper
`now_eval.prop_cofactor`): for a binary temporal with both arms purely
propositional, the left arm matters only on the positions where the right
arm has not yet fired, so restrict it to that care-set —
`φ U ψ → φ' U ψ` with φ' agreeing with φ on `{ψ false}` (W same);
`φ R ψ → φ' R ψ` agreeing on `{ψ true}` (M same, via `φ R ψ ≡ ¬(¬φ U ¬ψ)`).
φ' = Coudert–Madre restrict (`buddy.bdd_simplify(f, care)` — empirically
arg order is (f, care), NOT the manual's (d, f)) round-tripped through
BDD→ISOP, accepted only when strictly smaller. No temporal node
added/removed (Couvreur census untouched); wired after `_arm_unpad` in the
fold walk.

Motivating real case (polish/kinska sweep, 8ap-ba/randltl-10-a-hoa-5.txt,
source `h M e`): reference emitted `(e & !h) U (e & h)`; the rule reduces it
to `e U (e & h)`, which Spot prettifies back to `h M e`.

Tests: new `tests/kr/simplify/test_arm_cofactor.py` (10 shape+equiv cases,
SUCCESS); fold/now/factor/context suites CLEAN; `test_random_equiv.py`
500-formula fuzz ALL EQUIVALENT (28% changed); `test_kr_r4_audit.py` CLEAN;
`tests/survey.py` SUCCESS 35/35.

## 2026-06-16 — simplify rule 4: W/M expansion fold (DONE)

New independent fold in `fold_pass` (`_find_fold_or` / `_find_fold_and`,
commented there as logically separate from the X-unrolling folds): the
weak-until / strong-release laws `f W g ≡ Gf ∨ (f U g)` and
`f M g ≡ Ff ∧ (f R g)`, accepting the construction's ¬g-strengthened modal
body —
    G f         ∨ (f U g)   → f W g
    G(f ∧ ¬g)   ∨ (f U g)   → f W g      (sound: G(f∧¬g)∨(fUg) ≡ Gf∨(fUg))
and the duals to `f M g`. Body must be exactly f or f + a single ¬g
conjunct/disjunct; any other extra term makes G(body)/F(body) strictly
stronger/weaker (unsound, guarded + regression-tested). Trades two temporals
(G,U) for one (W) — an acc-set census win.

Chosen over a standalone pass (discussed): it IS a subcase of W-folding, and
inlining lets it compose with `_arm_cofactor` in the SAME bottom-up walk
(the U arm is cofactored before its parent Or is folded). So
`G(!b & h) | ((!b & h) U b)` → (cofactor) `G(!b & h) | (h U b)` →
(W-fold) `h W b`, recovering the source — the W/R analogue of the M-case
the cofactor rule already recovered.

Tests: new `tests/kr/simplify/test_wm_fold.py` (10 cases incl. 2 must-not-fire
guards, SUCCESS); fold/now/factor/context/arm_cofactor suites CLEAN;
`test_random_equiv` 500-formula fuzz ALL EQUIVALENT; `test_kr_r4_audit` CLEAN;
`tests/survey.py` SUCCESS 35/35.

## 2026-06-16 — simplify rule 4: GF/FG sibling cofactoring (DONE)

New independent rule in `fold_pass` (`_gffg_cofactor`, applied to boolean
nodes in the fold walk after `_fold_node`): under the cofinite invariant
`FG ψ`, the tail-only `GF φ` argument matters only where ψ holds —

    GF φ ∧ FG ψ   →   GF(φ|ψ)  ∧ FG ψ        φ restricted to {ψ true}
    FG α ∨ GF β   →   FG(α|¬β) ∨ GF β         dual (FG matters where β fails)

e.g. `GF(a&b) ∧ FG b → GF a ∧ FG b` (user's case). Care-set aggregates every
sibling invariant (`∧ ψ_k` for And; `¬(∨ β_k)` for Or), φ restricted via
`prop_cofactor` (Coudert–Madre + ISOP), accepted only when strictly smaller;
inner args must be propositional. No temporal node added/removed. Reuses the
`prop_cofactor` helper from the arm-cofactor rule.

Tests: new `tests/kr/simplify/test_gffg.py` (8 cases incl. Or-dual, nested,
2 must-not-fire guards — non-propositional arg + no-FG-sibling — SUCCESS);
all simplify suites CLEAN/SUCCESS; `test_random_equiv` fuzz ALL EQUIVALENT;
`test_kr_r4_audit` CLEAN; `tests/survey.py` SUCCESS 35/35.

## 2026-06-16 — wire own_simplify into the decompose recombiner (DONE)

The own-rules simplifier ran per kr-node and per leaf result, but
`portfolio/decompose._recombine` assembled the recombined And/Or and returned
it RAW — so a cross-part fold like `G(!b & h) | (h U b) → h W b` was never
attempted (no per-node pass ever saw that Or whole). Found via survey_diff:
the W/M + GF/FG rules unit-tested green but did NOT move the kinska sweep
output (`h W b` still emitted as `G(!b & h) | (h U b)`).

Fix: `_recombine` now runs `builders.own_simplify` (our rules ONLY — Spot's
tl_simplifier is deliberately excluded, it is not DAG-size aware) on each
part BEFORE combining and on the combo AFTER; the decompose recursion gives
both at every nesting level. Exposed a typed public `builders.own_simplify`
(wraps `_own_simp`: shared process bdd_dict, KR_SIMP_OWN size guard, no Spot).

Verified: `h W b`/`c W d` → source, `d R e` → d M e-fold, 8ap HOA → `h W b`.
survey.py SUCCESS (DAG 488→487); kr_r4_audit CLEAN; build_portfolio/
contract_combinators/options ALL OK/PASS.

## 2026-06-16 — LTL-definability gate moved off the sbacc form; Muller cap removed

- **Regression**: monolithic (non-`decompose`) cascade paths (`acc`/`weak`/
  `buchi`/`cobuchi`/`str`/`bls`) reported `NOT_LTL` for `GFa & GFb & GFc` — a
  formula written *in* LTL, so trivially LTL-definable. A false impossibility.
- **Root cause**: the gate (commit `fa900a2`) tested `IsAperiodicSemigroup` on
  the cascade's own `det_parity_sbacc()` automaton. Forcing STATE-BASED
  acceptance (`sbacc`) degeneralizes generalized-Büchi `Inf(0)&Inf(1)&Inf(2)`
  into a "which mark am I waiting for" counter — a real cyclic group in THAT
  automaton's transition monoid (GAP: 5 states, |T|=43, non-aperiodic), even
  though the language is LTL. Aperiodicity is a property of the SYNTACTIC monoid;
  the sbacc-inflated form is the wrong object. The same language in generic form
  is 1 state, |T|=1, aperiodic. The `conclusive = n <= sat_min_threshold` hedge
  was also unsound (small ≠ minimal, and `det_parity_sbacc` never SAT-minimizes).
- **Why `decompose` never misfired**: it splits the `&` into `GFa`/`GFb`/`GFc`
  *before* the gate, so no 3-way conjunct is ever degeneralized.
- **Fix** (gate on a sbacc-FREE form, before the build):
  - `language.py` — `Language` now HOLDS an `ltl_definable` `(definable,
    conclusive)` tag (`set_ltl_definable` / `ltl_definable`); it does not derive
    it (floor cannot import kr).
  - `kr/gap/aperiodic.py` (new) — `is_aperiodic_gens`: minimal GAP script
    (`Semigroup` + `IsAperiodicSemigroup`, NO holonomy), the cheap LTL oracle.
  - `kr/ltl_tester.py` (new) — `label_ltl_definable(lang)`: runs the oracle on
    `det_generic_minimal()` (deterministic, generic, SAT-min when small), caches
    the verdict on the Language. `conclusive` iff the form was state-minimal.
  - `kr/aut2cas.py` — the gate now runs `label_ltl_definable` BEFORE
    `decompose_lang` (skips the explosive holonomy build on non-LTL) and on the
    right form; the old post-build `casc.aperiodic` block + `_sat_min_threshold`
    are removed. One choke point for all cascade members (top + inner core share
    the single `as_translator`).
- **Muller cap removed** (`kr/cascade/config_graph.py`, `kr/options.py`): the
  good-Muller-set enumeration was capped by `KR_MULLER_SCC_LIMIT` (12), above
  which it emitted the whole-SCC set only — an APPROXIMATION that can build a
  non-equivalent formula. Removed entirely: enumeration is now always exact; if
  it explodes the run times out (honest), never approximates. The dead option is
  gone too.
- **Verification**: probes showed `GFa&GFb&GFc` 5-state/|T|=43/non-aperiodic
  (parity+sbacc) vs 1-state/|T|=1/aperiodic (generic); counting automata stay
  non-aperiodic on BOTH forms (no false negatives). R4 audit CLEAN. Survey sweep
  SUCCESS, 17/17 configs, zero `NOT_LTL` on the LTL corpus. Kinská sweep SUCCESS,
  strict improvement: 20 genuine `counting_buchi_*` cases that previously
  `BUILD_TIMEOUT` (build-first, then check) now report `NOT_LTL` quickly
  (cheap-check-first), 0 regressions. Reference baselines regenerated
  (`tests/logs/reference/20260616/`, kinská overwritten).

## 2026-06-16 — LTL simplify: completed the binary-modal expansion-fold quartet
The W/M expansion folds in `aut2ltl/ltl/simplify/fold_pass.py` covered only two
of the four laws (`f W g ≡ Gf ∨ (fUg)` at Or, `f M g ≡ Ff ∧ (fRg)` at And).
Added the two missing duals, both observed in real traces:
  - R-fold (Or):  `G(g ∧ ¬f) ∨ (f M g) → f R g`   (e.g. `G(!d & e) | (d M e) → d R e`)
  - U-fold (And): `F(g ∨ ¬f) ∧ (f W g) → f U g`
Both sound via the strengthened-body collapse (`G(g∧¬f)∨(fMg) ≡ Gg∨(fMg)`;
`F(g∨¬f)∧(fWg) ≡ Fg∧(fWg)`, the Gf branch of fWg killing g∨¬f). Each trades
two temporals for one (acc-set census win), same shape as the existing pair.
`tests/kr/simplify/test_wm_fold.py` extended (22 cases incl. must-not-fire for
the strictly-stronger/weaker extra-term variants); fuzz `test_random_equiv.py`
ALL EQUIVALENT, r4 audit CLEAN. README fold bullet rewritten to the 4-law quartet.
Other rules' duals confirmed accounted for (G/F absorption, GF/FG cofactor,
arm-cofactor U/W/R/M all present); the two deliberately-absent duals are the
S1/S2 W/M variants (unsound, regression-tested) and arm-padding's M case (sound
but never observed in outputs — arm-padding is empirically driven).

## 2026-06-17 — LANDED: result.py migration campaign complete; LTLFormulaResult retired

Completed the campaign tracked in TODO.md (steps 1–10). Every producer/combinator
now returns `aut2ltl/result.py::Result` (closed `Status` OK/DECLINED/NOT_LTL +
`credit`/`fuse`/`first` algebras per `result.md`); the legacy
`contract.py::LTLFormulaResult` dataclass, the `OK`/`DECLINED`/`NOT_LTL`/
`PROBABLY_NOT_LTL` status-string constants, the `_LEGACY_UNSUPPORTED` sentinel,
and `.conclusive`/`.note`/`not_ltl_definable` are all GONE.

- `contract.py` keeps only the `Translator`/`CascadeTranslator` Protocols, now
  annotated `-> Result`.
- `decompose.py::_recombine` reworked to the strict accumulator idiom
  (`fuse(start, *subs)` → bail-if-nok → fill formula), so a NOK fused with a NOK
  inherits BOTH diagnoses (the defect the user flagged: constructor-at-return
  dropped sibling reasons). `credit`/`fail` accumulate diagnoses via `_add_diagnosis`.
- `__main__.py` non-definability branch collapsed to a single `NOT_LTL` label
  (exit 3) printing `res.diagnosis`; decline test is now `not res.ok`.
- `PROBABLY_NOT_LTL` collapsed into `NOT_LTL` (proof-vs-hint wording lives in the
  diagnosis text). The Language-level `(definable, conclusive)` verdict in
  `language.py`/`ltl_tester.py` is a SEPARATE mechanism and stays; `aut2cas.py`
  folds its conclusive/hint qualifier into the `Result.not_definable(diagnosis=)`.
- Removed `Result`'s retro-compat harness (the `getattr(other, "note", ...)`
  duck-typing fallback in `credit`) now that no legacy result exists.
- Retired stale test scaffolding referencing the dead type: `tests/sl/probe_sl_core.py`,
  `tests/sl/probe_sl_over_str.py`, `tests/test_contract_combinators.py`,
  `tests/kr/test_acc_translator.py` (git rm; revisit only if needed).

Gates: `tests/kr/test_kr_r4_audit.py` CLEAN; `tests/survey.py` SUCCESS (35/35
validated, 0 false, 0 declined, DAG=487 temporals=119 build=8.8s).

## 2026-06-17 — daisy: pure self-loop core extracted as a peer translator

Lifted the pure marguerite/daisy core out of `aut2ltl/sl/sl_core.py` (`SlCore`) into
a new sibling package `aut2ltl/daisy/`, peer to `partscc`/`sccdecomp`: `daisy.py`
(the `Daisy(child)` combinator — peel one daisy = STAY∞ ∨ LEAVE, delegate stems to
the child), `shape.py` (the structure helpers `is_daisy`/`split`/`reroot`),
`algorithm.md` (clean spec, lifted from the "Algorithm presentation" half of
`sl/algorithm.md`), `__init__.py` (context-free, contract-only — names no siblings).
Naming converged through `slpeel` → **daisy** (memorable structural metaphor over a
descriptive compound; sets up the "daisy chains" big-self-loop extension); technique
tag is now `daisy`. Removed `sl/sl_core.py`; repointed the four probes (`probe_sl_core`,
`probe_sl_over_str`, `probe_inv`, `probe_sccdecomp`) to `aut2ltl.daisy.Daisy`. Still
unwired (probe-only, as `sl_core` was) — no STATUS shift. Verified via the probes
(`a U b`, `inv` over it, `sccdecomp` over it): all equiv=True, tag `daisy`.

## 2026-06-17 — decomp/: regroup the (de)composition approaches, themed by folder

Created aut2ltl/decomp/ as a theme folder, one self-contained subpackage per way of
breaking a language into easier pieces (each with its own algorithm.md, its own
inline recombine — nothing shared by force; decomp/__init__ imports none of them, so
one approach drags in neither its siblings nor their deps):

- decomp/scc/        — moved from aut2ltl/sccdecomp/ (SccDecompose; tag scc<k>).
- decomp/strength/   — NEW StrengthDecompose: ∨ over weak/terminal/strong (Renault
                       TACAS'13, exact for any automaton; tag strength<k>).
- decomp/acceptance/ — NEW AccDecompose: ∧ over acceptance conjuncts, exact on the
                       deterministic generic-minimal form (tag acc<k>).
- decomp/inv/        — moved from aut2ltl/inv/ (Invariant decorator); its doc
                       README.md → algorithm.md for folder parity.

strength + acceptance are the two halves of portfolio/decompose.py's AND/OR split,
re-cast as separate pure peer Translators (portfolio/decompose.py itself untouched —
still unwired). Verified via per-approach probes: Ga|Gb (scc3), Fa|Gb (strength2),
GFa&GFb (acc2), aUb (inv), all equiv=True. CLAUDE.md project-layout line updated.


## (archived) aut2ltl/kr/TODO.md — folded into history 2026-06-17

The kr TODO had become mostly a done-list; archived verbatim here and git rm-ed.

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

0. ~~**buchi2ltl on hash-consed `spot.formula` DAGs**~~ **DONE 2026-06-14.**
   buchi2ltl is now DAG-native end to end: `reconstruct_ltl` builds a hash-consed
   `spot.formula` DAG (t2 fragments included — `terminal_2scc` emits formula DAGs),
   and an adopted `scc_labeler` formula is spliced as a child node WITHOUT
   flattening. `sl_driven` drives it and its labeler returns the kr `spot.formula`
   DAG directly (no `str()`), so the kr-under-sl delegation boundary no longer
   flattens: `probe_sl_compose` all equiv=True, high-sharing cores stay tiny while
   kr-on-the-whole explodes — `XX(G(a->Fb))` 21 nodes vs 1.2×10¹⁴-tree,
   `c U (G(a->Fb))` 28 nodes vs TIMEOUT. Built as a temporary parallel module first
   and cross-oracled against the old string engine (MP ladder + randltl, 0
   divergences); the size census on the default decompose path is byte-identical to
   the pre-flush baseline (pure engineering refactor). The string engine and the
   cross-oracle (`reconstruction_dag.py`, `probe_dag_oracle.py`) were then DELETED;
   the engine was folded into `reconstruction.py` with the shared automaton helpers
   split into `reconstruction_helpers.py`. Gates green (r4 audit CLEAN, survey 70
   equiv=True / 0 fail). **Spin-off (agreed, next):** return a result struct with
   `.formula` + a `.technique` set (accumulating gate/and/or/buchi/cobuchi/bls/…)
   instead of a bare formula, and wire it into the surveys (see
   `[[technique-report-struct]]`).

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
   - ~~**F. per-conjunct Fin-reachability fold**~~ **DONE 2026-06-13**
     (`config_graph.configs_reachable_from`, used in the Muller-DNF assembly,
     default on, `KR_FOLD_FIN_REACH=0` restores). For a good Muller set M keep
     `Fin(C∉M)` only for C reachable from M in the config graph (drop the rest):
     `¬Fin(C∈M)` forces Inf⊇M, Inf is strongly connected, so C∈Inf ⟹ C∈reach(M)
     — C off the cone is implied finite. Pure graph check, no containment.
     **Subsumes the absorbing-M special case** (M absorbing ⟺ reach(M)=M) and,
     unlike it, (i) prunes Fin(C) on non-bottom M and (ii) decides the kept set
     BEFORE building `fin_c` (the explosive part) so dropped configs cost zero.
     **Bites the distinct-temporal census, not just the tree**: no-fold→on
     (absorbing-only in parens) — `a U b` 87→13 tree, 4→1 temporals (literal
     formula); `F(a&Xb)` 4251→2739 / **74→64** (abs 74, no change); `(aUb)|Gc`
     637→525 / 22→18; `Ga|Gb` 7026→6438 / 47→46; `Fa&Gb` 187→159 / 12→11;
     `G(a->Xa)` →141; `X(a&Xa)` →4134. Audit CLEAN, survey 0 fail / no
     regressions. Still over the 32-acc cap where they were (`F(a&Xb)` 64) —
     the kept `¬Fin(M)`/reachable-`Fin` part dominates (census-anatomy);
     deeper census reduction is the open P1 acceptance-dispatch job.
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
   in STATUS — gates green, fuzz 1500 ALL EQUIVALENT).
   ~~Rule 4: unroll-inverse folding~~ **DONE 2026-06-12** (fold_pass.py —
   expansion-law pair folds + first-occurrence/induction + S1/S2
   Formula-5 subsumption; the census-reducing realization of the
   "eventuality-aware rewriting" item: F(a&Xa) census 55→33, G(a->Xb)
   flipped survey True; numbers in STATUS). Refinement queue:
   ~~Context-aware subsumption~~ **DONE 2026-06-13** (initial-state
   opening + ctx_subsume; F(a&Xa) UNDER the 32-acc cap, census 26;
   numbers in STATUS). Remaining:
   - **eventuality census, remaining**: F(a&Xb) still 74 distinct
     temporals (cap 32). Next: deeper-shifted ladder forms (only the
     one-step shift is matched), and the multi-AP variants.
   - **opening flow direction**: one-way (earlier→later in canonical
     child order) misses openings whose source sorts after the target;
     alternating the direction across the pipeline's repeated context
     passes is sound (each pass a fixed direction) and would double
     coverage — needs the direction in the context-pass memo key.
   - giant nodes are skipped by the cap, so the X(a&Xa)/reactivity wall
     is barely moved — needs either O(n) factoring on big Ors or the
     C/D/E fold candidates. NB the cap measures UNFOLDED tree size; with
     per-node memoized passes a DAG-size cap is the honest poly bound
     and would let the top of big formulas be processed.
   - fold pass changes memo keys → construction takes different paths
     (X(a&Xa) unfolded count moved both ways across tools); re-baseline
     the size censuses in kr/testing/logs/.
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

- **Acceptance dispatch per construction-ref §9.3 — IN PROGRESS, THE ACTIVE
  FRONT (orthogonal module `kr/acceptance_dispatch.py`). Resume here.**
  The Muller DNF (`Δ₂`, the default) is the explosive form; Theorem 2 gives a
  direct φ per acceptance class that drops the Fin web. Dispatch table (det
  class → frag → φ): looping-coBüchi/`Σ₁`/`⋁reach_to(ι,C)`;
  looping-Büchi/`Π₁`/`⋀¬reach_to(ι,C)`; weak/`Δ₁`/`⋁_G end_in(G)`;
  coBüchi/`Σ₂`/`⋀_{C∈α}Fin(C)`; Büchi/`Π₂`/`⋁_{C∈α}¬Fin(C)`; Muller/`Δ₂`/full
  DNF. The looping/weak forms use `reach_to` (NO Fin); Büchi/coBüchi keep ONE
  Fin per accepting config (no `Fin(C∉G)` web, no good-set enumeration).
  - ~~**Büchi (`Π₂`)**~~ **WIRED on the default path — 2026-06-13.**
    `reconstruct_buchi(casc)` = `⋁_{C∈α}¬Fin(C)`, returns None if not
    `acc().is_buchi()`. Hooked as a TOP-LEVEL pre-check at the head of
    `reconstruct_ltl_paper_style` (gate `KR_DISPATCH_BUCHI`, default ON; `=0`
    restores pure Muller) — NOT in `reconstruct_bls`, because the GOTO decompose
    front end calls `reconstruct_ltl_paper_style` directly per piece, so the
    single pre-check covers both entries and fires per single-condition piece.
    α is COVER-AWARE (`config_graph.buchi_accepting_configs` off
    `build_pruned_config_aut`, not the lift-section `accepting_configs()`):
    the wiring exposed the cover caveat below — `F(a&Xb)` first went equiv=FALSE
    (`L⊊L(orig)`, lift α missed the duplicated accepting sink) and the cover
    reader fixed it. Gates: audit CLEAN, survey 0/35 FALSE / four walls flipped
    True / zero regressions, size A/B `G(p->(qUr))` 84→14 temporals (totals −22%,
    tractable-cases −61%); numbers + logs in STATUS. ~~Cover caveat~~ RESOLVED.
  - ~~**coBüchi (`Σ₂`)**~~ **WIRED — 2026-06-13.** `reconstruct_cobuchi(casc)` =
    `⋀_{C∈α}Fin(C)` (α = `config_graph.cobuchi_finite_configs`, the cover-aware
    DUAL of the Büchi reader), as a SECOND pre-check after Büchi in
    `reconstruct_ltl_paper_style` (gate `KR_DISPATCH_COBUCHI`, default ON). **GATE
    is the crux:** Spot's parity step hides coBüchi as `Inf(0)|Fin(1)`
    (`is_co_buchi()` False), so the gate recovers the natural acceptance via
    `postprocess(.,"generic")` and tests `is_co_buchi` there — and this MUST be
    measured UNDER decomposition (the raw `decompose_aut` view both misleads on
    the gate and overstates size: sat_minimize ~halves `FGa|FGb`). The
    `postprocess(.,"coBuchi")` gate is UNSOUND (GFa passes it). Results: `FGa`
    6→3 / `F(a&Gb)` 7→4 / **`FGa|FGb` 6195→2779 temporals** (still over the cap,
    UNVERIFIED — the residual is reach-driven) / reactivity `(GFa&FGb)` 10→7
    (its persistence AND-piece dispatches); totals −40%. Survey 0/35 FALSE, only
    `FGa|FGb`'s UNVERIFIED size changed; audit CLEAN. Numbers + logs in STATUS.
  - ~~**looping/weak (Δ₁/Σ₁/Π₁)**~~ **WIRED but OFF by default — 2026-06-13
    (`KR_DISPATCH_WEAK`).** `reconstruct_weak` = `⋁_G end_in(G)` (pure `reach_to`,
    no Fin; subsumes looping safety `⋀¬reach_to(sink)` / guarantee
    `⋁reach_to(sink)`), gate `is_weak_automaton(postprocess(.,"generic"))`, placed
    BEFORE Büchi/coBüchi (which else claim weak langs first). Correct (flag-on
    survey 0/35 FALSE) but a SIZE REGRESSION, so kept OFF: probes
    (`probe_weak_dispatch`, `probe_looping_dispatch`) show general worse 6/7,
    dedicated looping mixed (2 wins / 3 losses). The residual on weak cases is
    REACH-driven (τ-tail), which no acceptance form touches — looping just swaps
    the Fin-web for `reach_to` at the same cascade depth. Kept in as the A/B
    baseline for the Acc(c) idea below.
- ~~**config-indexed `Acc(c)` for the weak/bounded class**~~ **DONE — WIRED,
  default ON (2026-06-13, `KR_DISPATCH_ACC`).** `reconstruct_acc` = `Acc(ι)` by
  bounded unroll (R1 ⊤/⊥ Spot oracle on the small input D + R2 one-step unroll),
  SELF-GATING (declines → BLS on any recurrent config), first in the dispatch
  chain. **Cracks `X(a&Xa)`: UNVERIFIED 5.1×10⁸ → equiv=True, literal output**;
  whole X-ladder collapses to the literal; recurrent cases decline. Survey: only
  `X(a&Xa)` changed (UNVERIFIED→True), 0/35 FALSE, zero regressions; audit CLEAN.
  Numbers + logs in STATUS. Remaining items spun off:
  - **Replace the Spot ⊤/⊥ oracle with a structural test.** R1 currently uses
    `is_empty`/`are_equivalent` on D-from-q (bounded, small input, but a Spot call
    in the construction path — the one departure from "Spot for hash-consing
    only"). A graph test — q ⊥ iff no accepting state reachable from q; q ⊤ iff no
    rejecting behaviour reachable (on the deterministic complete D) — would keep
    the construction Spot-free. Soundness-check before swapping.
  - **Per-config (not whole) fallback at recurrent configs.** Acc currently bails
    the WHOLE construction to BLS on the first recurrent config (clean for the pure
    bounded fragment). A transient-prefix + recurrent-core input would benefit from
    splicing BLS/dispatch only at the recurrent configs (`Acc(c) = BLS-from-c`
    there), extending Acc past the pure-bounded class. Mind the cover/state-vs-config
    map when splicing (cf. the Büchi cover caveat).
- ~~**Last MP-survey wall: `FGa|FGb`**~~ **CRACKED by the buchi2ltl gate
  (2026-06-14): 2779→3 temporals, equiv=True; MP survey now a clean sweep.** The
  persistence-union the cascade/decompose path could not split is handled
  directly by buchi2ltl's backward labeling on the raw (nondeterministic) form.
  See STATUS "buchi2ltl heuristic gate". Spin-off items below.
- **buchi2ltl gate — wired, default ON (2026-06-14, `kr/heuristic_gate.py` +
  `decompose_recombine`). Landed; refinements:**
  - **Spot ⊤/⊥-style dependence is now just the bounded TGBA `postprocess` in
    the gate** (language-preserving, on the small node) — acceptable like Acc(c).
    No per-call equiv check (sound-by-construction, audited 0/0 over ~170 randltl
    via `fuzz_gate_decompose.py`); `KR_GATE_VERIFY` keeps the audit one env away.
  - ~~**gate-vs-split order**~~ **gate goes UNDER decomposition now
    (2026-06-14, `KR_GATE_UNDER_DECOMP`, default ON).** Decompose FIRST, gate the
    leaves; raw-form gate only when the root does not split (the
    determinization-sensitive cases — measured in `probe_gate_redet.py`). This
    fixed the honesty bug the size census exposed: a case `split_report` called
    `or(2)` used to be taken whole by the gate (`tech=sl`), now it actually
    decomposes (`tech=or+sl`). Size A/B (`survey_sizes_underdecomp` vs
    `survey_sizes_method`): wash (DAG 494→491, temporal 114→119) — OR-unions
    tighter (`Fa|Gb` tree 13→8), AND-conjunctions un-factored (`GFa&GFb` vs
    gate-whole `G(Fa&Fb)`, +1 temporal), all under cap & stylistically equal.
    Parked: per-node pick-smaller (build gate-whole AND decomposed, keep fewer
    temporals) would recover the AND factoring; not worth it at these magnitudes.
  - **technique reporting (`ReconResult`) — DONE 2026-06-14.** `reconstruct_decomposed`
    and buchi2ltl's `reconstruct_ltl` return `kr.recon_result.ReconResult`
    (`.formula` + `.technique` set), wired into both surveys' `tech=` column.
    Cross-package import edge (buchi2ltl→kr) deferred to a shared `util` —
    `[[technique-report-struct]]`.
  - **adopt rate ~81%** on random formulas; the ~19% it declines (and the
    UNVERIFIED giants) are exactly the REACH/cascade cases kr carries — the two
    paths are complementary, gate for shape-friendly + decomposition, kr for the
    systematic fallback.
- **Decompose-and-recombine at the root — LANDED + now the goto path
  (2026-06-13, `kr/decompose_recombine.py`; numbers in STATUS).** Both splits
  implemented and validated; `reconstruct_decomposed(aut)` is the survey default
  (`KR_DECOMPOSE=1`). Sound because kr is language-faithful and a ROOT operator
  is a pure position-0 language op: `L(A)=⋃L(Aᵢ) ⟹ ⋁ kr(Aᵢ)` / `⋂ ⟹ ⋀`.
  - ~~**OR-decompose by STRENGTH**~~ DONE (`decompose_scc` w/t/s, union =
    language; Renault TACAS'13): `Ga|Fb` 499→21 tree (True), `(aUb)|Gc`
    6.97M→637 (True flipped from UNVERIFIED).
  - ~~**AND-decompose by ACCEPTANCE SET**~~ DONE (`top_conjuncts()` on the det
    acceptance; determinism makes `acc=⋀cᵢ ⟹ L=⋂L(A|cᵢ)` exact): `GFa&GFb`
    9.08e16→111 (True flipped), `(GFa&FGb)` 2⁶⁰→True, `GFa&GFb&GFc` unbuildable
    →compositional SOUND, `G(a->Fb)&G(c->Fd)` True at L=7.
  - Open-checks resolved: (1) the conjunctive form is `translate/postprocess`
    deterministic-GENERIC (not parity); split BEFORE parity normalization.
    (2) per-piece census is small (each single-Büchi piece ~10 temporals).
    (3) front-end wrapper `_to_split_form`→dispatch→`⋀`/`⋁`. NEW finding: kr's
    census is acutely state-count-sensitive, so `_to_split_form` must
    `sat_minimize` the det automaton (AUTOMATON-only — `GFa&FGb` 2-state
    postprocess explodes to 9.5e15, 1-state sat_minimize → 313).
  Remaining work:
  - ~~**export from `kr/__init__.py`**~~ DONE — `reconstruct_decomposed` /
    `split_report` exported; README documents `reconstruct_decomposed(aut)` as
    the recommended top-level entry (automaton in, formula DAG out).
  - **acceptance ABSORPTION** blocks both splits when Spot's determinization
    folds a second component into one set/strength: `GFa&Gb` (recurrence ∧
    safety → single `Inf(0)`, `none`, stays 89 temporals over cap) and
    `FGa|FGb` (persistence union → single co-Büchi, `none`, 2⁶⁰). Need a way
    to expose the absorbed component as a separate conjunct/strength, or a
    different split basis for these.
  - **n≥3 verification**: the recombined `⋀` trips Spot's 32-acc cap; the
    compositional check (`kr(pieceᵢ)≡L(pieceᵢ)`) is the sound witness — wire it
    into the survey as the verdict for over-cap recombinations (currently only
    in `probe_and_decompose`).
  Lineage: same root-soundness that makes `φ ∧ kr` sound when the INITIAL state
  carries an arbitrary φ; decomposition is that applied to ⋃/⋂.
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
- **NOT_LTL detection — IN PROGRESS (2026-06-15).** Non-LTL inputs (kinská
  `counting/`) currently get a WRONG formula from the cascade leaves (the
  holonomy group component is mislabeled `KIND reset`); SL correctly declines.
  Oracle: `IsAperiodicSemigroup(T)` on D's transition monoid (LTL ⟺ counter-free
  ⟺ aperiodic). Contract `NOT_LTL` / `PROBABLY_NOT_LTL` landed; wire GAP emit →
  parse → cascade flag → leaf members → portfolio/`__main__`. Conclusive only
  when D is state-minimal (`PROBABLY_NOT_LTL` above the SAT-min threshold).

## P4 — heuristic/kr mixin via suffix-formula injection (LOW PRIO, deferred)

Revisit only once the main census-wall path (P0 folds + P1 acceptance
dispatch) is stable. The idea: hand a hard component to a heuristic that
returns a formula φ_q labeling a state q of the original aut, then splice φ_q
into the kr reconstruction at the precise time points where the construction
"enters" q (config c with `state_of(c)=π(c)=q`; the config↔state map is the
traceability bridge — `state_of`/`state_to_config` already exist). Cleanest
realization: STUB q to terminal-accepting (its sub-automaton reduces to True,
the cascade handles the trivial residual) and conjoin φ_q once at the
`reach_strong(c,…)` arrival, UNDER the arriving X.

Conclusions from the 2026-06-13 exploration (what kinds of φ / side effects
work, and why — keep these; the exploratory code was reverted):

- The augmented language is `L(A) ∩ L(G(at_q → φ))`, `at_q` a deterministic
  state predicate. Always ω-regular; the question is whether kr can inject φ
  WITHOUT paying an exponential.
- kr has NO localized "language-from-q" subterm Ψ_q — it characterises
  acceptance globally (Muller DNF over i.o. config sets + reach/Fin). So
  "AND φ on top of what kr asserts at q" is well-defined as a LOCAL edit only
  where q's contribution collapses to one point: a terminal stub (Ψ_q=True)
  or a single transient (Fin) arrival. (Contrast: compositional
  state-elimination / the buchi2ltl backward labeling DO have L(q), so their
  `scc_fragments` splice is trivial — `buchi2ltl/reconstruction.py`.)
- SOUND + cheap to inject locally  ⟺  φ is ACCEPTANCE-NEUTRAL at q:
  * safety/invariant φ (small deterministic monitor; the extreme case is
    G(inv), a 1-state monitor) — does not perturb the Muller condition; only
    the loop encoding must be un-fused to expose the per-visit hook
    `G(at_q_letter → φ ∧ …)` (a size cost, NO exponential);
  * terminal stub — q stops participating in acceptance, so φ is asserted
    once at the single arrival.
- NOT a free lunch for LIVENESS φ at a RECURRENT q: the correct meaning
  `G(at_q → φ)` changes the acceptance question, forcing the product A×B_φ and
  re-derivation of the Muller condition. The exponential reappears in the
  product's recurrent structure — kr pays for acceptance, and renaming the
  liveness as "a formula on q" does not move it out of the Muller machinery.

Concrete from the attempt (reverted, recorded here): per-state downstream
invariants are computable by live-edge constancy on the aut (skip sinks =
states not co-reachable to an accepting SCC), validated against a semantic
oracle (`L` restarted at q ⊨ G(inv_q)); `a & XGb` is caught at the post-a
state (init has none). The GLOBAL front-end peel (project a forced literal
out of the input aut, run the chain, recombine `& G(inv)`; `Fa & Gb` 12→2
census, equiv=True) was DROPPED on purpose — it is the "poor man's" degenerate
case (init-config invariant only) and not the direction we want; per-config
injection above subsumes it when/if pursued.

## 2026-06-17 — session: tool-first docs, contract/combinator refactors, decomp/ + kr→bls reorg

Cleared from TODO.md as DONE:
- Root README rewritten tool-first (+ rendered example image docs/img/); aut2ltl/README.md
  source map added; bls/README rewritten as a current source map.
- contract.py split: Translator -> aut2ltl/translator.py (the floor, no implementor
  refs); CascadeTranslator -> aut2ltl/bls/cascade_translator.py; contract.py kept as a
  deprecated shim.
- combinators.py -> first_success.py. result.md folded into the result.py module
  docstring (the .md removed).
- decomp/ regroup: one isolated subpackage per (de)composition approach — scc
  (ex-sccdecomp), strength, acceptance (extracted from portfolio/decompose), inv
  (moved in). daisy/ extracted from the old sl_core (slpeel -> daisy).
- kr engine reorg + rename: members foldered (acc/weak/buchi/cobuchi/muller); operators/
  gathers the reachability operators + Fin(C); the reachability.py shell + README.old
  removed; kr/STATUS -> docs/kr_STATUS.md, the kr TODO folded into this file. Then
  kr/ -> bls/ (the BLS construction names the engine); the general member is `muller`,
  bls.py a deprecated shim.
All verified: CLI + tests/survey SUCCESS + the r4 audit CLEAN throughout.

## 2026-06-18 — heur/fuse2: extracted the size-2 SCC over-approximation (groundwork for retiring sl/)

The f2 size-2 non-accepting-SCC over-approximation heuristic (legacy
`aut2ltl/sl/heuristics/size2_overapprox.py::try_size2_overapprox`) moved to a new
theme package `aut2ltl/heur/` (pattern-matching heuristics) as `heur/fuse2`.

WHY: the portfolio rework wants `sl/` and the current `portfolio/` contents to
disappear entirely (all of sl is covered by `daisy`, a stronger version of the same
self-loop labeling). f2 was the one piece of sl with no daisy equivalent, so it is
lifted out first, cleanly, with no dependency on `sl/`.

WHAT: reframed HONESTLY as what it is — a gated TGBA->TGBA rewrite, NOT a Translator
(produces no LTL). `fuse2(aut) -> twa_graph | None`: find one non-accepting 2-state
SCC, unfold it once over-approximating the satellite self-loop to true, return the
result ONLY if `spot.are_equivalent` confirms the language survived. Documented
WIP/immature: best-effort, fires rarely, only ~30% of accepted rewrites actually
linearize into daisy reach (the rest stay multi-state, daisy declines harmlessly) —
the gate guarantees language equality, never the target shape.

CLEANUP vs legacy: `get_true_bdd` formula-translation hack -> `buddy.bddtrue`; one
200-line function -> four typed helpers + a thin gated entry; all F2_TRACE prints
dropped. `tests/heur/test_fuse2.py` proves byte-for-byte behavioral PARITY with the
legacy entry over the 100-formula f2 fixture (0 disagreements, 0 gate failures).

NOT WIRED: nothing imports `heur/` yet; the live pipeline + survey/r4 gates are
untouched. Decision: leave unwired for now, let fuzzing measure whether its absence
costs perf vs the current default before deciding to wire it.

## 2026-06-18 — portfolio/builder.py + simplify_ltl: the `best` recipe takes shape (--use best)

Started the portfolio rework as a NEW assembly file rather than retiring the old one
in place. `aut2ltl/portfolio/builder.py` holds named "recipes" (good assemblies found
in exploration) as convenience builders over the translators:

  bls(options)   = as_translator(make_hierarchy_class(options))  -- the cascade
                   engine lifted, with the cached LTL-definability gate in front.
  daisy(child)   = fixpoint first(Daisy(self), child) -- recursively peel self-loop
                   daisies, floor on `child` (the proven probe idiom).
  best(options)  = Simplify(strength(acceptance(daisy(bls))), "hi") -- the modern
                   re-expression of the historical Decompose/SlDriven/Decompose graph,
                   daisy in place of the sl envelope.

`RECIPES` maps recipe names; `build_portfolio` resolves a lone `--use best` to the
named assembly (recipes are whole assemblies, not ladder rungs). The CLI/survey can
now run `--use best` and variants head-to-head.

NEW COMPONENT `aut2ltl/simplify_ltl/` (Simplify Translator decorator): forwards to a
child, simplifies an OK formula (`lo`=own DAG rules, `hi`=+Spot tl_simplifier), NOK
passes through. Lives outside `ltl/` to respect the dep graph (a Translator must
import the contract floor, which `ltl/` may not). It GENERALIZES the two inline
`_simp_f(cand)` calls the historical `Sl`/`SlDriven` ran on their own padded output
(portfolio/sl.py, sl_driven.py).

SURVEY (--use best vs the default reference, 40-formula corpus): SUCCESS, 0
regressions, sound (39/40 validated, 1 Spot >32-acc wall). The one `hi` outside
collapsed the broad small-case padding (movers 17->5; several now SMALLER than
default). Remaining +138% DAG is essentially ONE formula: G(a->Xb) 6->101, because
partscc/t2 is not yet wired and it routes to the buchi cascade. NOT the default yet;
additive via --use best.

## 2026-06-18 — partscc wired into `best`: --use best reproduces (and edges out) the historical default

Wired `aut2ltl.partscc` into the `best` recipe via a `core` floor:
`core = first_success([PartScc(), bls])`, handed to the daisy fixpoint as its
delegate (`daisy(core)`). partscc labels a single terminal SCC — exactly what a daisy
peel hands an exit target — and is the modern replacement for the sl `t2` heuristic.

RESULT (survey, 40-formula corpus, `--use best` vs the default reference
tests/logs/reference/20260616_2/default.csv):
  * SUCCESS, 0 regressions, 40/40 VALIDATED equivalent (was 39/40 — the lone
    spot_err was the G(a->Xb) buchi blowup hitting Spot >32 acceptance sets; partscc
    (DAG 6) sidesteps it).
  * DAG 487 -> 539 (+10.7%), tree 1940 -> 2036 (+4.9%) — down from +138%/+1440%
    before partscc. Only 4 changed rows; 3 are WINS over the default (GFa&GFb&GFc
    -20%, (aUb)|Gc -15%, GFa&GFb -14%), one +1 node (GFa&FGb). Faster too (9.1s).

MILESTONE: `best` = Simplify(strength(acceptance(daisy(first(partscc, bls)))), hi)
now reproduces the historical Decompose/SlDriven/Decompose default with daisy in place
of the whole sl envelope and partscc in place of t2 — the goal of the portfolio
rework. Still additive (--use best); promoting it to the no-flag default and retiring
sl/ + the old portfolio contents is the remaining work (see TODO).

LOG NOT COMMITTED: tests/logs/best.csv is throwaway scratch (WIP), not promoted to
the reference baseline — promote only when best becomes the default.

## 2026-06-18 — simplify: strong-until/release as FG/GF invariant source

`_gffg_cofactor` (ltl/simplify/fold_pass.py) generalized: the FG/GF cofactoring
invariant source now also recognizes a strong `U(_, G(x))` on the And side and its
dual `R(_, F(x))` on the Or side, not just the literal `FG x` / `GF x`. Sound because
`φ U G(x) ⟹ FG x` for any φ (the strong until forces the eventuality); dually a false
`φ R F(x)` gives `¬φ U G(¬x) ⟹ FG ¬x`, the same `¬x` co-invariant `GF x` supplies.
Weak `W`/`M` are excluded — their `Gφ`/`G¬φ` branch breaks the entailment (regression-
tested as must-not-fire).

WHY: tracing the lone `GFa & FGb` mover where `--use best` was +1 over the historical
default (8 vs 7 DAG). NOT a decomposition difference — `and2` (legacy) and `acc2` (new)
run byte-identical splits and meet identical automata; the daisy leaf emits FGb as the
U-form `1 U Gb`, which the cofactoring rule did not see as an `FG` invariant, so the
cross-part collapse `GF(a&b) ∧ FGb → GFa ∧ FGb` never fired and the outer Spot pass
factored to `G(FGb & F(a&b))` (8). With the rule extended, `GFa & FGb → G(Fa & FGb)`
(7) through the simplifier alone — no per-leaf simplify crutch in `builder.best` (an
inner-`hi` experiment that reached the same 7 was backed out; the fix belongs in the
rule). best now ties-or-beats the default on every corpus formula: −49.6% DAG, 40/40
sound, 0 regressions, 0 size-losses (survey scratch tests/logs/best_rulefix.csv, WIP).
Gates: gffg 12/12, fold CLEAN(42), random-equiv fuzz 500/500 equivalent, R4 CLEAN.

## 2026-06-18 — simplify: algorithm.md spec, README slim, producer-first context order

Documentation + one behaviour tweak, all on the simplify package (`aut2ltl/ltl/simplify`):

- **`algorithm.md`** (new) — a decomp-style construction/soundness spec for the four-pass
  simplifier (context / now-eval / factor / fold), written by reading each module back,
  not from the README: the root-equivalence soundness model, every rule with its
  soundness hook, the pipeline pseudocode, termination-by-orientation, O(DAG) cost.
- **`README.md`** slimmed ~195→~60 lines to a source map + usage (mirrors `bls/README`);
  spec delegated to algorithm.md. Docstring cross-refs repointed (and the stale
  `kr/simplify` path fixed).
- **`context_pass.py`** — children are now visited **now-fact producers first**
  (`_open_rank`, polarity-aware: G/R/M at And, F/U/W at Or, strong before weak). The
  one-way opening (sound, anti-circular) made the result depend on canonical child
  order; producer-first maximises how many siblings each opening reaches. Free (Spot
  re-canonicalises the rebuilt node; tiny operand lists). Fuzz: marginally more
  reduction, ALL EQUIVALENT; survey corpus DAG unchanged (538), R4 CLEAN.

WHY: reviewing the simplify code while writing the spec surfaced the order-sensitivity
of the one-way now-fact opening — sound but order-dependent in completeness. The
producer-first sort is the cheap, principled answer (strong facts reach the weak
siblings that consume them); no soundness change, the fixed-order invariant holds for
any order.

## 2026-06-18 — tests/benchmark: the portfolio evaluation bench (collection phase)

A new sub-project to strengthen evaluation beyond the 40-formula survey gate: a SIZE
bench comparing portfolios (`default` vs `best`) at scale, reusing the survey engine.

- **`inputs/`** — raw file corpus, category subfolders, `.ltl` (one formula/line, `#`
  comments) / `.hoa` / `.md`-ignored: `core/` (the survey corpus by MP class,
  `from_survey.py`), `chains/` (W/U/R chains ± X-lacing, `patterns.py`), `kinska/` (105
  Büchi HOA, flattened + deduped from 125, `collect_kinska.py`).
- **`normalize.py`** — AP-canonical NAME form (rename APs to a,b,c… by first
  occurrence, NOTHING else — no simplification/reorder/minimisation), the dedup key for
  LTL and HOA. Deduped Kinská 125→105 (cosmetic key); whole corpus 164 items / 164
  unique.
- **`bench_sweep.sh`** — `default` vs `best` over `inputs/`, then `survey_diff.py`.
  Logs default to the gitignored `tests/benchmark/logs/`; reference runs committed
  under `tests/benchmark/logs/reference/`.

Engine/test changes this session, all landed:
- **survey summary reworked** for honesty: "aut2ltl answered X/Y (LTL built + not-LTL)"
  vs "Failures (timeout/crash/declined)", then a separate Spot-validation line
  (EQUIVALENT / not-checked grouped as "formula too large") with **NOT EQUIVALENT** on
  its own prominent line. not-LTL now counts as us answering; Spot's size wall no longer
  reads as self-doubt. Uniform across all sweeps.
- **`survey.run_build`**: a run that REACHES the budget is `BUILD_TIMEOUT`, not `CRASH`,
  whatever the exit code — the tool's SIGINT handler (proc.py reaps GAP, re-raises) can
  exit outside timeout's 124/137. A genuine crash exits fast and is still `CRASH`.
- **simplify**: `_gffg_cofactor` accepts strong `U(_,G x)` / `R(_,F x)` as FG/GF
  invariant sources; `context_pass` visits now-fact producers first; `ltl/simplify`
  gained `algorithm.md`; README slimmed. (Earlier entries this date.)

FINDING: the first full bench run flagged a legacy-`default` **FALSE** (verified
non-equivalent) on the strong-until chain `(a U ((a & b) R (b | c)))`, which `best`
reconstructs correctly — concrete evidence to promote `best` and retire the legacy path.

## 2026-06-18 — promote `best` to the default (portfolio pivot)

`build_portfolio(options, techniques=None)` now returns `RECIPES["best"](options)`
instead of `_default_portfolio` — so the no-`--use` path IS the modern `best` recipe
(`Simplify(strength(acceptance(daisy(core))), "hi")`, `core = first(partscc, bls)`).
WHY: the `tests/benchmark` first full run caught the legacy `Decompose / SlDriven /
Decompose` default producing a verified-FALSE (non-equivalent) formula on the
strong-until chain `(a U ((a & b) R (b | c)))` via `or2+or3+sl+sl_driven`; `best`
reconstructs it soundly (`daisy+strength2`, DAG 19, Spot True). Gated: kr r4 audit
CLEAN, survey SUCCESS 40/40 equivalent (all modern techniques), and the formerly-FALSE
formula now sound under the default CLI path. `_default_portfolio` and the legacy
`sl`/`sl_driven`/`decompose` rungs are now dead pending the architecture retirement.

## 2026-06-18 — retire the sl engine + legacy portfolio; settle the --use vocabulary

Full-modern cleanup on top of the promote-best pivot. DELETED: aut2ltl/sl/ entirely
(the heuristic backward-labeling engine — daisy subsumes its self-loop labeling,
partscc its t2 SCC heuristic, fuse2 was already extracted to aut2ltl/heur);
portfolio/{decompose,sl,sl_driven,options}.py (Decompose / Sl / SlDriven / the
portfolio.sl.* OptionSpecs); the aut2ltl/bls/bls.py compatibility shim (hierarchy_class
now imports muller directly). build.py dropped _default_portfolio and the
sl/sl_driven/decompose vocabulary; portfolio/__init__ is a modern surface
(build_portfolio/TECHNIQUES/RECIPES, _options seeded from KR_OPTIONS); __main__ dropped
PORTFOLIO_OPTIONS. VOCABULARY settled: the six producers acc/weak/buchi/cobuchi/muller/bls
+ recipe best — `str` became `bls` (the integrated cascade) and the old `bls` general
leaf became `muller` (its acceptance class). TESTS refreshed (one-time, per user):
deleted the tests/sl/ probes + test_sl_member + kr/test_decompose + kr/fuzz_gate_decompose;
rewrote test_build_portfolio + test_options; repointed test_fuse2 to drop the retired-
legacy parity (keeps the soundness gate). The curated example corpora already lived in
tests/fixtures (f2_successes still used by test_fuse2; t2_successes + terminal_2scc_labeled
kept though now orphaned). survey_sweep.sh + READMEs/STATUS/TODO/CLAUDE updated. Gates
green throughout (survey SUCCESS 40/40, kr audit CLEAN).

## 2026-06-18 — benchmark: fixtures import + AP-canonical corpus + keyed diff (LANDED)

Grew tests/benchmark from 164 -> 373 inputs and made the stored corpus uniform.
- WHY: the bench set was thin and inconsistently named (kinska HOA carried randltl
  alphabet letters like "g"; survey core used p,q,r), which muddied basic dedup.
- WHAT: new collect_fixtures.py ports tests/fixtures/*.py (formulas / f2_successes /
  t2_successes / terminal_2scc, 206 formulas after cumulative AP-normalized dedup vs
  the rest of inputs/ excl. kinska) + the 3 fixture HOA. The basic AP rename
  (normalize.py) is now APPLIED on store by every generator: collect_kinska (was
  verbatim), from_survey, patterns. No simplification/reordering — pure rename.
- Investigated the kinska "8ap" redundancy: it was a filename misread (randltl's
  candidate alphabet, not declared APs); the automata declare <=2 APs and use them,
  so remove_unused_ap was a near no-op (verified structurally inert) — dropped that
  idea, kept only the basic rename.
- survey_diff.py rewritten (pandas): keys on the input column, reports key-set
  overlap (absent-left/right, common, answered counts), diffs the common fragment.
- Sweep at 15s clean: 366/373 answered, 0 not-equivalent, 0 regressions vs the prior
  reference on the common fragment; reference baseline refreshed.

## 2026-06-18 — daisy2 (length-1 star peel) + best_daisy2 becomes the default

LANDED a new translator `aut2ltl/daisy2/` generalizing `daisy` by one level: it
peels a whole **length-1 star SCC** (a hub with petal self-loops, stem exits, and
one-hop spokes — each spoke a one-state daisy reached by `E_s ∧ X(G_s U R_s)`,
a strong `U`). The move-level closed form is not yet solved, so daisy2 emits a
candidate and adopts it only if a Spot equivalence oracle confirms it (the
`partscc` gate pattern) — always sound, currently **gate-rescued**. Design lives
beside the code in `aut2ltl/daisy2/algorithm.md` (moved there from
`daisychain/algorithm2.md`); the general multi-state design stays in
`daisychain/algorithm.md`.

Construction notes worked out this session (all in daisy2/algorithm.md):
- **S1/S2** drop FVS (hub given) and restrict detours to length 1 (the star).
- **S3** (keystone): acceptance marks only on the petals/links, never on the q1
  self-loop — checkable; makes revisit-of-hub a *theorem* (looping q1 collects
  nothing ⇒ non-accepting ⇒ must return) and makes acceptance a clean **per-edge
  `GF` anchor** at the move boundary (Target A, DONE).
- Open nut: the safety `StaySafe` is still the unsound flat-`G`; the
  position-0-anchored `Φ_stay` fixpoint (the hub anchor) is the single missing
  piece — it would also fix the acceptance phase case `GF(a&Xb)`.

PORTFOLIO: `best_daisy2` = `best` with the **daisy/daisy2 peel pair** (`daisy_pair`)
in place of `daisy`; wired `best_inv` (the global-invariant `G(Σ)` layer, which was
in NO recipe before). On the 373-case benchmark (core/chains/fixtures/kinska) all
recipes are sound (0 non-equivalent); best_daisy2 is −3.6% DAG vs best and turns
`!a M G(b|X(b R a))` from a 3804-node UNVERIFIED blob into a verified 16-node
formula. best_inv is benchmark-neutral on this corpus (~0.03%) but kept as an A/B.
**best_daisy2 is now the no-`--use` default** (`build_portfolio`); reference
baseline regenerated (DAG 538 → 414 on the 40-survey).

## 2026-06-19 — best_of brick + LTLResult.cost; best_inv_all experiment

WHY/WHAT. Landed `best_of` (`aut2ltl/best_of/`), the choice-by-size sibling of
`first_success`: runs every stage, returns the least-`cost` OK result (NOT_LTL
short-circuits as an absorbing verdict; DECLINED falls through; ties keep cited
order; winner returned unchanged, name is identity). A dedicated brick package with
its own README, mirroring `recurse/`. Added `LTLResult.cost` — the DAG-node count of
the result formula (lazy, cached, invalidated by the formula setter), the
provisioned "output size" field the result-contract NOT-FINAL note anticipated; the
metric import is local to keep the contract floor decoupled. `best_of`'s default
`key` is `cost` but is swappable. Unwired so far. KNOWN: `dag_node_count` is noisy at
the margin (the `(a U b) | Gc` inv case is 11→12 yet better-factored) — a switch
margin + a refined scalar are deferred (TODO) before wiring it into a recipe.
Test: `tests/test_best_of.py` (GAP-free) green.

Also added `best_inv_all` (`portfolio/recipes/best_inv_all.py`), an experimental
recipe weaving `Invariant` at every boundary (top, around `Acc` pre-determinization,
and per peel descent via `daisy_pair_inv`). Survey: sound (40/40 equiv, 0 regress),
inv fires on 16/40, DAG +0.7% (flat at survey scale; the pre-determinization strip
is a benchmark-scale lever). Default recipe pointer made a single re-pointable alias
`RECIPES["default"]`; recipes split one-module-per-file under `portfolio/recipes/`.

## 2026-06-19 (same day, follow-up) — best_of: pluggable Comparator, drop cost field

Reshaped best_of after the design firmed: the selection policy is now a single
pluggable `Comparator` (a `Protocol`, not a Callable alias) — `beats(incumbent,
challenger) -> bool` over two whole LTLResults. INTENT framed in its pydoc: all
weighed results denote the SAME language, so a comparator only ever picks a better
FORM, never changes what is expressed (sound by delegation — a preference, not a
gate). Walk is incumbent-in-order: first OK trusted, a later OK takes over only when
beats() says so. Comparators moved to best_of/comparators.py (the catalog): `smaller`
(strict-min DAG size) + `significantly_smaller(rel, floor)` (guidance margin:
inc-ch >= max(floor, ceil(rel*inc)) — strict on small, proportional on large).
DROPPED the LTLResult.cost field added earlier the same day: the two-result
comparator makes an embedded score redundant, and deriving size in the comparator
(dag_node_count(.formula)) keeps the contract floor free of the metric layer. README
extended: intent, a comparator catalog table, and how to configure/write another.
Still unwired. tests/test_best_of.py green.

## 2026-06-19 — combinator algebra, Step A: vocabulary (identity, compose, Decorator)

Plan enchanted-dreaming-hopper, step A of D. Named the decorator sort of the
combinator algebra: `Decorator` Protocol in aut2ltl/translator.py (Translator ->
Translator, beside Translator), and aut2ltl/compose.py with `identity` (the ∘ unit,
distinct from the decline terminal) + `compose(*decorators)` (outermost-first,
compose(f,g,h)(x)=f(g(h(x))), empty=identity). Free named combinators only — no DSL,
no operators. Additive (nothing imports compose yet). tests/test_combinators.py green
(identity neutrality, compose order/assoc/unit); r4 audit CLEAN.

## 2026-06-19 — combinator algebra, Step B: point-free recipes

Plan step B of D. All 5 portfolio/recipes/*.py rewritten from inside-out nested
constructor calls to flat `compose` terms, e.g.
best_inv_all = Simplify(compose(Invariant, StrengthDecompose, Invariant, AccDecompose,
daisy_pair_inv)(core(options)), "hi") — the two Invariant inserts now visible in the
list. Simplify stays the outer wrap (it takes the "hi" level arg). Pure move: survey
SUCCESS, DAG=414 unchanged, all --use recipes resolve identically. r4 audit CLEAN.

## 2026-06-19 — combinator algebra, Step C: unify the three decomposers

Plan step C of D. New aut2ltl/decomp/decompose.py: combine(connective, tag, parts)
(the shared _recombine = fuse + root ∧/∨ + own_simplify) and decompose(split,
connective, tag) -> Decorator (= recurse(λself.λlang. combine(...,[self(Language.of(p))
for p in split(lang)]) if split(lang) else leaf(lang))). strength/acceptance/scc
collapse from byte-identical class+_recombine scaffolding to one-liners over their kept
split fns: StrengthDecompose=decompose(strength_pieces∘tgba, Or, "strength"),
AccDecompose=decompose(conjunct_pieces∘det_generic_minimal, And, "acc"),
SccDecompose=decompose(<accepting_sccs+restrict_marks>, Or, "scc"). Behavior-preserving
(the three _recombine were byte-identical modulo connective/tag): survey SUCCESS
DAG=414 unchanged, r4 CLEAN. The .name class attr dropped (nothing read it; tags come
from combine's LTLResult.start). decomp's recurse body is a *combine* (∧/∨); daisy's is
a *choice* (⊕) — same fix, different body op.

## 2026-06-19 — combinator algebra, Step D: COMBINATORS.md + close-out (DONE)

Plan step D of D — campaign complete. New top-level COMBINATORS.md: the (almost-)
algebra over language-manipulators as a conceptual lens — carrier (Translators
faithful-or-⊥), the two sorts (translators / Decorators), the operations
(⊕ first_success / ⊞ best_of / ∘ compose / fix recurse, + the ∧/∨ combine of
decompose), the neutrals (decline terminal / identity ∘-unit), the ONE law (soundness
closed under every op) and the NEGATIVE laws loud (⊕ non-commutative, ⊞-with-margin
non-associative, fix no monoid), and the daisy(choice body)/decomp(combine body)
contrast. Close-out: removed the prepended COMBINATOR-ALGEBRA plan block from TODO.md
(A-D all landed), trimmed the superseded "recurse/fix combinator (idea)" item to the
still-open memoization lever, flipped the STATUS combinator-algebra note to done,
removed the algebra_todo.md scratch. Scope held throughout: free named combinators
only, no DSL/AST/meta. Whole campaign behavior-preserving (survey DAG=414 unchanged).

## 2026-06-19 — cake recipe: the liberal best_of (first best_of wiring)

First wiring of best_of into a recipe. cake (portfolio/recipes/cake.py) = best_of over
[best_daisy2 (trusted incumbent), best_inv_all (inv everywhere), an scc_variant that
finally wires the orphaned SccDecompose ∨-split], beats=significantly_smaller(rel=0.25,
floor=2). Liberal in ingredients, but the guidance margin only displaces the default on
a significant form win, so it is pure upside. Survey --use cake: SUCCESS, 40/40 equiv,
DAG=412 (vs default 414 — best_of harvested 2 significant wins, kept the safe form
elsewhere). Also defaulted best_of's name kwarg (="best_of") so it is frictionless to
wire. Not the default; curate the best*/cake recipe set later.

## 2026-06-19 — cake: decomposition BELOW daisy (the deep variant)

cake's aggressive alternative reshaped: the `scc_variant` (scc only above the peel)
became `deep` = compose(Strength, Acc, daisy_pair, Strength, Acc, Scc)(core) — decomp
BOTH above daisy AND below it: the peel now delegates its residuals to a fresh
Strength∘Acc∘Scc stack before the bls core, instead of the bare core (where the default
only re-peels). Terminates (the below stack floors on core, a leaf; no re-entry into
daisy). Survey --use cake: SUCCESS, DAG=412 vs reference default 414 (-0.5%, 0
regressions; one win: Fa & Gb 7->5 via the inv variant clearing the margin). The deep
below-daisy decomp did not fire on the 40-formula survey (too small) — it is a
benchmark-scale lever; here it is confirmed sound and wired. Diffed with
tests/survey_diff.py vs tests/logs/reference/default.csv.

## 2026-06-19 — cake slimmed: shy best_of, one cascade (partscc-floored rich variant)

Benchmark verdict on the 3-assembly cake: every win was inv (daisy+inv / inv+partscc,
none needed bls); the deep below-daisy decomp + standalone scc won nothing; ~1.8x cost
+ a kinska counting NOT_LTL->TIMEOUT from running bls TWICE per case. Reshaped to two
stages where best_of hides only ONE cascade: best_daisy2 (full core, run first so its
NOT_LTL short-circuits) + a RICH cheap variant weaving every technique
(compose(Invariant, Strength, Scc, Invariant, Acc, daisy_pair_inv)) that floors on
PartScc ONLY (no bls) — declines to the incumbent where partscc cannot label, so no
second cascade. Curated-40 survey --use cake: SUCCESS, DAG=412 (keeps the Fa&Gb inv
win), build 3.75s ~= default 3.7s (was 1.8x). Re-sweeping bench+kinska to confirm.

## 2026-06-19 — cake adopted as the default

After the lean (one-cascade) cake cleared the bar on the full benchmark — Pareto over
best_daisy2: 11 wins (-25..-41%), 0 regressions, 366/373 answered (+1 vs the old
default's 365), build 136.5s ~= default 140s; kinska size-identical (the lone counting
NOT_LTL->TIMEOUT is a shared 14s-vs-15s budget oscillation: the reference logs 14.003s
and the default itself times out under load) — repointed RECIPES["default"] = cake (the
single-line alias). Gate after: default resolves, r4 audit CLEAN, curated-40 survey
SUCCESS DAG=412 (was 414). STATUS updated. Reference logs regenerated under the new
default next.

## 2026-06-19 — daisystar (rejecting-star reachability peel); cakeds is the new default

LANDED `aut2ltl/daisystar/` — a peer combinator translator for the **reachability**
regime daisy2 deliberately declines. Motivating gap: `F(a & X b)` fell through every
structural peel to the bls/buchi leaf, a 181-node blob, versus a handful of nodes.
Its automaton is a non-accepting star {0,1} above a trivial accepting sink, exiting
the star from a SPOKE on the trigger b — i.e. the language is pure reachability.

The construction is the *easy half* of daisy2: when the initial SCC is **rejecting**
(Spot's `is_rejecting_scc`), no run staying in it forever accepts, so `STAY∞ = false`
**by construction** — daisy2's open `Φ_stay` safety closed form never arises. Only the
`LEAVE` least-fixpoint remains: `stay U ⋁(exit moves)`, with the exit allowed to fire
from inside a spoke (`E_s ∧ X(G_s U (h_k ∧ X φ_k))`), the return-excursion shape with
the return replaced by a spoke-stem. The flat `stay` region reuses daisy2's
move-level form, so `LEAVE` is still gate-rescued (Spot equivalence, the partscc
pattern); always sound. shape.py allows spoke-exits and ignores marks (the two
differences from daisy2's star_partition). algorithm.md is written in the complete
daisy-style (not the daisy2/daisychain draft style).

WIRED via `daisy_trio`/`daisy_trio_inv` (daisy → daisy2 → daisystar) in
portfolio/builder.py and a new `cakeds` recipe (= cake with the trio peels).
Benchmark A/B (default=cake vs cakeds, 373 inputs, survey_diff): **0 regressions,
10 equivalence fixes** (BUILD_TIMEOUT / UNVERIFIED_SIZE cases now Spot-verified),
**DAG −78.5%** (e.g. `(a U b) M XF!a` 23123→18, `F(Fa & (!a M (a U b)))` 18721→15,
`F(a & Xb)` 181→13); curated 40-survey SUCCESS, r4 audit CLEAN. Promoted cakeds to
`RECIPES["default"]`.

Also de-referenced the current-default recipe NAME from README / portfolio/README /
CLAUDE.md / STATUS CLI section — the single source of truth is the
`RECIPES["default"]` pointer; docs that named the winner went stale (best_daisy2 →
cake → cakeds).

## 2026-06-19 — daisystardet peer + cakedsdet default (LANDED)

Promoted the deterministic anchored read-off `DaisystarDet` from a sub-module of
`daisystar` to its own peer package `aut2ltl/daisystardet/` (daisystardet.py +
shape.py + __init__.py + algorithm.md, the spec history-free; reroot reused from
daisy, flat-LEAVE attribution corrected daisy->daisystar). Re-pointed
`RECIPES["default"]` from `cakeds` to `cakedsdet`. WHY: over the `cakeds`
reference the deterministic read-off is a clean Pareto step — survey -3.3% DAG (0
reg), 373-case benchmark 9 equivalence fixes / DAG -22.6% (counting_buchi
2150->13, several -90%+ cases), kinska -15.9% DAG (0 reg); the lone kinska
NOT_LTL<->BUILD_TIMEOUT diff is 15s-cap jitter, not a read-off effect. Audit
CLEAN, survey SUCCESS. Regenerated the three reference baselines (survey /
benchmark / kinska) under the new default. Also decoupled
tests/test_build_portfolio.py from the recipe name (asserts the "default" alias,
not a hardcoded name) so future adoptions touch only RECIPES.

## 2026-06-20 — never-regress round trip + ltl2tgba size guard

LANDED. New brick `aut2ltl/memo/` (`Memo`: transparent per-instance WeakKeyDict
cache, share-on-hit, identity-on-results; pushed). Recipe `roundtrip_best` =
`best_of([Memo(C), Roundtrip(Memo(C))])`, one shared Memo, registered `--use
roundtrip_best` over cakedsdet (naive `roundtrip` kept for A/B).

Guard: ltl2tgba dies on exp-flat formulas; the round trip fed huge SEEDs back in
mid-construction (real inputs tiny, so never hit before). `Language._base` now
gates the formula-translate via `_guard_translation` on unfolded(flat)-tree /
temporal-op knobs (env-seeded, tree 100 / temporal 32, 0=off; tree measured
capped at limit+1 since tree_node_count saturates), raising
`UntranslatableLanguage` (unchecked) before the call. `Roundtrip` catches it on
the relabel -> decline (best_of keeps plain); `__main__` catches the escapee
(e.g. user input over budget) -> declined bottom carrying the limit, prints like
a decline, exit 1.

Bug it fixed: at no guard, exp seeds -> false NOT_LTL / timeout / crash (7+9+1
across genaut/bench/kinska). Tuned 50->100 after 50 erased sound wins.

Bound=100 vs reference, roundtrip_best, 0 regressions ALL corpora: core +0%,
kinska +0% (seeds>100, parked = syntactic-decomp room), bench -14.7% DAG / tree
-94.5%, genaut -85.5% DAG / tree 1e32->9e8. Motivator aut_33300 seed 31 tree /
4 temporal -> 5 (collapses at any bound>=31/4). Audit CLEAN, survey SUCCESS.
5 commits on master, NOT pushed (memo 3 commits pushed earlier).

## 2026-06-20 — tests/ restructure, part 1: probes extracted + the import architecture

Began a large tests/ restructure separating three tangled concerns: the survey
HARNESS, the module PROBES, and the sample DATA. Part 1 extracted the probes —
and turned out to hinge on a question the plan never anticipated: how the test
code finds aut2ltl.

LANDED (one bulk move + follow-ups):
  * Moved the per-module probe folders (bls, daisy2, daisychain, daisystar,
    daisystardet, heur, inv, language, partscc, sccdecomp, the smoke scratchpad)
    and the root-level test_*.py unit tests under a single tests/probes/ home.
  * Decided the import architecture (the pivotal, unplanned piece):
      - `pip install -e .` makes `import aut2ltl` resolve anywhere (editable =
        dev mode = installed, same thing). setuptools gives a STRICT editable
        finder (maps only aut2ltl*, does NOT leak `tests` onto sys.path).
      - Probes are NEVER installed. They run as `python -m tests.probes.<...>`
        from the repo root: cwd carries the live source (incl. undeclared
        modules, no install friction) and sibling `tests.*` corpora resolve.
      - Consequently DELETED every per-file `sys.path.insert(... parents[N] ...)`
        bootstrap (~44 files) — the move had silently broken all the parents[N]
        depths anyway. The convention replaces them. Documented in
        tests/probes/README.md ("run with -m from the repo root").
  * Modernized the gate (test_kr_r4_audit): drop the bootstrap, locate
    reachability_operators.py via the module's own __file__ instead of a
    PROJECT_ROOT path. Runs CLEAN under `python -m tests.probes.bls.test_kr_r4_audit`.

CONSIDERED THEN DROPPED:
  * Extracting survey's bounded-subprocess runner (run_build core) into a shared
    survey/constrain_run.py for the probes' crash-isolation subprocesses. Moot
    once the only probes using that pattern were retired (below); survey keeps
    run_build to itself.

RETIRED (probe rot, surfaced by actually running them under -m):
  * test_kr_zoom — targeted removed internals (reconstruct_bls renamed
    reconstruct; aut2ltl.bls.reachability._compute_good_muller_sets moved to
    aut2ltl.bls.cascade).
  * test_kr_basic, test_kr_reconstruct, trace_fin_semantics — algo-invention-era
    scaffolding (hand-rolled subprocess crash-isolation + bootstrap, called
    reconstruct_bls). Superseded by the survey harness (end-to-end equivalence
    over corpora) + the standing gate audit. Retired with thanks.

BORN (step 3 started early, out of order):
  * survey/diff — the directional language-comparison tooling (ltl_diff +
    diff_hoa) turned out to be reusable HARNESS tooling, not module probes, so
    it left tests/probes/bls for a new top-level survey/ package, exportable as
    a module path: `from survey.diff import diff_report, to_aut` (lazy PEP 562
    re-export so running a submodule via -m doesn't trip runpy's double-import
    warning). This plants survey/ (the aut2ltl evaluation harness, a client of
    aut2ltl). Rename to aut2ltl_survey / pyproject wiring deferred.

PLAN REORDER: do step 3 (survey/) BEFORE step 2 (samples/) — the harness infra
(how it discovers/descends a folder, where it writes logs) dictates the shape of
the samples/ and logs/ trees, not the other way round. READMEs come LAST, once
stable; given how intense this refactor is, they will likely be rewritten from
scratch rather than curated step by step.
