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
