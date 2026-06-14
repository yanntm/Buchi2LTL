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

## P-ARCH — aut2ltl contract layer + engine separation (NEXT, active 2026-06-14)

**Context / why.** The project has grown to ~15 flat `kr/` modules (~3900 LOC) +
the separate `buchi2ltl/` engine, and recent iterations turned it into a
PORTFOLIO: a HOA is translated by whichever method wins at each node — the
buchi2ltl gate, AND/OR decomposition, or one of the leaf acceptance forms
(acc/weak/buchi/cobuchi/bls). The sl⇄kr mixing is genuinely mutually recursive
at RUNTIME (kr-under-sl via `sl_driven`'s `scc_labeler=reconstruct_decomposed`;
sl-under-kr via `decompose_recombine`→`heuristic_gate`→buchi2ltl). But the only
STATIC import edge between the packages is `buchi2ltl → kr.recon_result`
(everything else is runtime callbacks). The tangle exists only because the
mixing code lives INSIDE `kr/` and reaches sideways into `buchi2ltl/`.

**Vision (contract-first).** Make a new top-level **`aut2ltl`** that DEFINES THE
CONTRACT — the data + behavioral signatures of "translate a HOA to LTL" — and is
the user front-end (HOA in, formula out, lots of flags). `kr`, `buchi2ltl`, and
the portfolio strategies become IMPLEMENTATIONS of that contract.
- **The data signature: `ReconResult`** — `formula` + `technique` (set[str]) +
  an explicit `status` (OK / DECLINED; no more `UNSUPPORTED` smuggled inside
  `.formula`). Reified as a struct precisely so it is EXTENSIBLE (add a
  `cost`/size field when the pick-smaller combinator needs an ordering, etc.).
- **The behavioral signature: `Translator`** — `translate(twa) -> ReconResult`
  (DECLINED status = "not me"). Contract invariant (not type-checkable):
  language-faithful OR declines, never wrong. That single rule is what makes
  composition sound.
- **The algebra = combinators that are themselves `Translator`s over
  `Translator`s** — the system is a COMPOSITE + DP: a tree of Translators
  (leaves = buchi2ltl, kr's acceptance forms; combinators = Gate(primary,
  fallback) / Decompose(leaf) / SlDriven(core) / Portfolio([…], key=cost)),
  with the recursion's value MEMOIZED (the hash-consed `spot.formula` DAG +
  per-subproblem caches). Every current entry point (reconstruct_decomposed,
  sl_driven, the gate, even kr's acc→…→bls FirstSuccess chain) is one expression
  in this algebra; `.technique` is the trace of which leaves fired.

**Why this dissolves the cycle.** Lifting the mixing UP into `aut2ltl` (the
composition root) and the contract DOWN into a floor both engines depend on makes
`kr` and `buchi2ltl` PEERS that import neither each other nor the root. Layers,
acyclic: **contract floor → engines (kr, buchi2ltl) → combinators → composition
root / CLI.** The mutual recursion stays — as a runtime EXPRESSION the root
assembles — which is exactly where "the cycle is normal" belongs.

**Settled decisions (2026-06-14).** (1) explicit `status` on `ReconResult`, not a
formula sentinel; (2) the struct is the extension point — add fields (cost/size)
when a combinator needs them, no separate side-comparator; (3) `technique` is an
open `set[str]`; (4) combinator PLACEMENT is deferred — decide it from the actual
code as we refactor (cross-engine combinators likely up in `aut2ltl`,
intra-engine dispatch likely stays in the engine, but read it off the code);
(5) clean API separation is the goal — Protocol vs ABC vs registry is just the
Python realization, chosen when we implement.

**Target layout (refined 2026-06-14, user direction — SIBLING packages, decided).**
- **`kr/`** = ONLY the pure cascade-based FoSSaCS construction (the holonomy/Muller
  engine): cascade, reachability(_operators), fin, config_graph, acceptance_dispatch,
  gap_bridge, extract, ltl_builders, bdd_utils, simplify/. ALL heuristics leave it.
  `kr` stops exporting `reconstruct_decomposed`; its public API is the pure engine.
- **the heuristic engine** (buchi2ltl's sl/f2/t2 backward labeling) stays a separate
  sibling package.
- **`decompose/`** (its own folder — likely the composition root) = the portfolio /
  combinators: `decompose_recombine`, `heuristic_gate`, `sl_driven`. Mixes the two
  engines; owns the runtime mutual recursion.
- **contract floor** = `ReconResult` + `Translator`, in a shared place both engines
  and the portfolio import (today `kr/recon_result.py`; to be lifted out so `kr`
  proper has no portfolio coupling). Resolves the `buchi2ltl→kr` edge
  (`[[technique-report-struct]]`).

**THE MOVE CAMPAIGN — finalized 2026-06-14, IN PROGRESS. Checkpoint-approved
(pause + show + get commit OK at each natural checkpoint). Decisions locked:**
NESTED root package `aut2ltl/`; heuristic engine named `sl/`; `evaluate.py` →
`tests/eval_roundtrip.py`; `samples/` → `tests/fixtures/`. `git mv` everywhere
(preserve blame). Gates green at each checkpoint: `test_kr_r4_audit` CLEAN +
`survey_mp_cascade` clean sweep. Layering (acyclic): `aut2ltl/contract.py` ←
`{aut2ltl/kr, aut2ltl/sl}` ← `aut2ltl/portfolio` ← `aut2ltl/cli` + `__init__`.

Target tree:
```
aut2ltl/
  __init__.py  contract.py(ReconResult/Translator)  cli.py
  kr/      pure cascade FoSSaCS engine (cascade, config_graph, extract,
           gap_bridge, reachability(_operators), fin, acceptance_dispatch,
           ltl_builders, bdd_utils, gap/, simplify/) — heuristics REMOVED,
           no portfolio exports
  sl/      heuristic engine (was buchi2ltl/: reconstruction(_helpers),
           invariants, utils, heuristics/)
  portfolio/  decompose_recombine, heuristic_gate (the kr↔sl seam), sl_driven
tests/     kr/ (was kr/testing/ +simplify/testing +examples), sl/ (was top
           testing/), fixtures/ (was samples/), eval_roundtrip.py
```

Steps (mark done inline as we go; ~46 files import `kr`, ~17 import `buchi2ltl`,
mostly tests; internal relative imports survive a whole-package `git mv`):
1. Scaffold `aut2ltl/__init__.py` + `.gitignore` (__pycache__, *.pyc, gen artifacts).
2. `git mv kr aut2ltl/kr`; rewrite external `kr` imports → `aut2ltl.kr`. GATE.
3. `git mv buchi2ltl aut2ltl/sl`; rewrite `buchi2ltl` imports → `aut2ltl.sl`. GATE.
4. `git mv aut2ltl/kr/recon_result.py aut2ltl/contract.py`; repoint importers. GATE.
5. `git mv` decompose_recombine/heuristic_gate/sl_driven → `aut2ltl/portfolio/`;
   trim `aut2ltl/kr/__init__.py`; add `portfolio/__init__.py`. GATE (the load-bearing
   one: r4 audit + MP survey).
6. Consolidate tests: kr/testing→tests/kr, kr/simplify/testing→tests/kr/simplify,
   kr/examples→tests/kr/examples, top testing→tests/sl, samples→tests/fixtures,
   evaluate.py→tests/eval_roundtrip.py; fix script imports. GATE from new paths.
7. `git mv buchi2ltl.py aut2ltl/cli.py`; repoint.
8. Delete (history-recoverable): root current_*.csv/results.csv/trace_aut_*,
   old_results/, testing/*.csv + debug_images/, kr/examples/generated/*, empty kr/tests/.
9. Docs: CLAUDE.md, README.md, kr/README→aut2ltl/kr/README, STATUS/TODO pointers,
   memory project_kr.

**Incremental, code-driven plan (superseded above by the concrete campaign;
kept for the rationale). Each step small; gates green after each —
`test_kr_r4_audit` CLEAN + `survey_mp_cascade` previously-True stay True.**
1. ~~**Reify the contract in place (no folders move yet).**~~ **DONE 2026-06-14.**
   `ReconResult` got an explicit `status` (OK / DECLINED) + `decline()` /
   `.declined` / `.ok`; the `UNSUPPORTED`-in-`.formula` sentinel is gone from the
   contract boundary (engines still use the string INTERNALLY in their recursion,
   translated to DECLINED at the boundary return). Migrated call sites:
   `buchi2ltl.reconstruction.reconstruct_ltl` (boundary return), `heuristic_gate`,
   `sl_driven`, the two root CLIs (`buchi2ltl.py`, `evaluate.py`). The `Translator`
   Protocol (callable `twa -> ReconResult`, invariant "language-faithful OR
   declines, never wrong") is written down in `recon_result.py`. A transitional
   legacy-string sniff in `.declined` keeps every intermediate state green; drop it
   once nothing emits the sentinel at a boundary. Gates: r4 audit CLEAN, MP survey
   0 failing / clean sweep (`logs/survey_parch_step1_2026-06-14.txt`). Reading the
   call sites confirmed the seams: the only static cross-edge is the boundary
   `buchi2ltl→kr.recon_result` import; everything else is the runtime callbacks.
   Standing convention from this step: type signatures explicitly (user pref).
2. **Then decide the first folder move from what step 1 taught us** — the contract
   floor (`ReconResult`/`Translator`) out of `kr/` into the shared place both
   engines import, since that is the only static cross-edge. Resolves the deferred
   `[[technique-report-struct]]` import-edge item.
3. **Move the portfolio (the "daddy") up** — `heuristic_gate`,
   `decompose_recombine`, `sl_driven` out of `kr/` into the `decompose/` layer;
   `kr` stops exporting `reconstruct_decomposed` (its public API shrinks to the
   pure algebraic engine). Combinator shape emerges here.
4. **Fold the root CLIs** (`buchi2ltl.py`, `evaluate.py`) into the front-end with
   the flag surface.

**Open / to decide as we go.** (a) ~~nested vs sibling~~ DECIDED: SIBLING packages
(`kr` + heuristic engine + `decompose` + contract floor top-level). (b) does
`buchi2ltl` keep its top-level identity or become "the sl engine" alongside `kr`;
(c) whether the CLIs collapse into one `cli.py`; (d) combinator placement (likely
all in `decompose/` since the mixing is cross-engine). Expect iteration.

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
- Counter-free verification for external HOA inputs (GAP IsAperiodic) — stretch.

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
