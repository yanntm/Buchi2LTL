# kr/ Current Status

Factual snapshot of the current state. History lives in `git log`; work items in
`kr/TODO.md`; doc map in `kr/README.md`.

## Pipeline (done, general)

- `decompose_aut`: Spot norm to det complete min-even parity with **state-based
  acceptance** (`sbacc` — soundness requirement: the Muller condition is lifted over
  configurations, so the infinitely-visited state set must determine acceptance)
  → generators (explicit 2^|AP| letters) → GAP/SgpDec holonomy → parsed `Cascade`.
- **True-cascade extraction (2026-06-11, the Ga|Gb root-cause fix):** the GAP
  script now emits (i) the state lifts via `AsHolonomyCoords(s, sk)` — the old
  `AsCoords(s, hcs)` is `DomainOf(hcs)[s]`, an enumeration accident unrelated
  to point s; (ii) the **true transitions**: generators lifted with
  `AsHolonomyCascade` acting via `OnCoordinates`, BFS-closed from the lifts
  (TRANS lines); (iii) the cover map π via `AsHolonomyPoint` (PI lines).
  Holonomy coordinatization is a many-to-one **cover**, so config dynamics
  cannot be reconstructed by conjugating D through the lift (the old shortcut
  produced non-reset "cascades": for Ga|Gb, `!a&b` acted as {1→1,2→1,3→4,4→4}
  on a level — impossible in a reset cascade; all earlier passing cases were
  degenerate, i.e. context-free consistent). Parse REVERSES coordinates
  (SgpDec is top-first with deeper levels reading upper state; the operators
  peel index 0 first with suffix as the self-contained sub-cascade) — verified
  by `kr/testing/probe_reset_consistency.py`: post-fix the suffix convention
  is exactly the reset-consistent one.
- `Cascade`: levels, state↔config (1-based), letter valuations, `move_config`
  (explicit transition table when present — closure may be strictly larger
  than the lift image, e.g. Ga|Gb sink covered twice; legacy h-conjugation
  fallback only for old outputs), Enter/Stay/Leave helpers, pruned config
  automaton, accepting configs.
- Good Muller sets: enumeration of strongly-connected **accepting subsets** of
  non-rejecting SCCs of the pruned config aut (`acc().accepting(in-M edge-mark union)`
  oracle, exact under sbacc; `KR_MULLER_SCC_LIMIT=12` gate, logged whole-SCC fallback).
- Stability: `bdd_utils` buddy-var precompute + per-case subprocess isolation in tests.

## Operators — LITERAL paper forms, spot.formula objects end-to-end

All five formulas are now the literal constructions of paper Sec 4.2 /
construction-ref §7 (the former from-S / first-step approximations are gone):

- `_stay_gt0_strong` = solid⁺: last-step decomposition over combined letters
  ⟨σ,T'⟩ enumerated over ALL h-image configs (`_combined_letters_at_level`),
  lower-level prefix reach to T', stay enforced by Leave-avoid conjuncts,
  bad-predecessor conjuncts.
- `_dashed_change_strong` = Formula 5 lines (1)+(2)+(3): Enter(t)/Enter(b)/Leave(s)
  as combined letters, lower prefix reaches, parameterized-bad line(2) with the
  SWAPPED wsolid, line(3) solid-to-leave-point. No s==t guard (leave-and-return).
- `reach_weak` = the literal dual ¬reach(S,T,τ,B,β) (old G(τ|¬β) base was wrong:
  Table 1 gives τ R ¬β). The bespoke `_dashed_change_weak` was a non-paper
  invention and is deleted.
- `_solid_stay_weak`/`_stay_gt0_weak` = literal wsolid/wsolid⁺ (lines (1)+(2),
  no free-reach, wreach avoids); the s≠t early-false was removed (wrong for
  weak: degrades to "never blocked"). Case dispatches compare FULL configs.
- `fin_c` per Lemma 7 with working ι==C postponement.
- **No string round-trips (P0-perf step 1 done):** all operators + fin_c accept
  and return hash-consed `spot.formula` objects (str still accepted at entry
  for probes); one shared `spot.tl_simplifier` (persistent cache) does at most
  one simplify per operator return; `_str_f` is a pure stringifier; assembly
  in `reconstruct_ltl_paper_style` builds formula objects (fin_c computed once
  per config, reused across Muller terms) and stringifies only the final
  result. The `PAPER_STYLE_TOO_LARGE` sentinel guard is gone — the real
  formula is always returned; callers run equiv checks under timeouts.

## Semantic validation state (trace_fin_semantics grounding)

Grounding is now **cover-aware**: GTs are built on the config semiautomaton
(the closure graph — the actual cascade run space), since with π many-to-one
"visits config C" is strictly finer than "visits state π(C)" (per-state GTs
gave spurious under-approx BADs on duplicated sinks).

- **GFa: ALL SUB-TERMS GROUNDED OK** (1L regression green).
- **G(a -> X b): zero contradictions** on the true cascade; 4 sub-terms
  UNVERIFIED (Spot blocked under the per-check timeout — megabyte flat
  serializations, see below), every check that completes is OK.
- **Ga | Gb: zero contradictions** (was 11 BADs pre-fix — the case that
  exposed the cover bug); 5 sub-terms UNVERIFIED for the same Spot reason.

## Open problem: Spot-side verification of large outputs (size = serialization artifact)

Construction is NOT the bottleneck (`kr/testing/measure_formula_dag.py`, true
cascades): G(a->Xb) 0.08s / 1173 DAG nodes / 3.8MB flat / 192 distinct
temporal subformulas; Ga|Gb 0.08s / 988 nodes / 5.0MB flat / 191. The flat
unfolding (sharing factor >1200x) and the one-acceptance-set-per-temporal-
subformula tableau hit Spot's 32-acc-set hard limit (fast error) or blow the
translation/complementation time on big sub-terms. Test scripts now carry a
built-in Spot budget (`KR_SPOT_EQUIV_TIMEOUT` / `KR_CHECK_TIMEOUT`, default
10s) and report SPOT_TIMEOUT / UNVERIFIED — *distinct from a semantic
failure* — so blocked-verification is never mistaken for blocked-construction.
Spot authors have been contacted about leveraging heavily-repeated
subformulas in translation (our DAGs are tiny; any sharing-aware approach
would shine here). Until then: TODO P0-verify (fewer distinct temporal
subterms, compositional checking, word sampling).

## Survey snapshot (2026-06-11, post true-cascade extraction)

- Spot-checked end-to-end equiv on the new pipeline: `Fa`, `GFa`, `a U b`,
  `Fa | Gb` **True**; audit gate CLEAN.
- **`Ga | Gb`: FIXED semantically** (zero grounding contradictions; true
  sizes [4,3], 5 closure configs). End-to-end equiv unverifiable by
  translation (32-acc-set fast error) pending P0-verify.
- Full `survey_mp_cascade.py` ladder re-run pending (now reports
  construction and Spot phases separately).

## Tooling for targeted work

- `kr/testing/survey_mp_cascade.py` — MP-class × depth ladder; construction
  and Spot-equiv phases in separate subprocesses with separate budgets
  (`KR_CONSTRUCT_TIMEOUT` 30s / `KR_SPOT_EQUIV_TIMEOUT` 10s).
- `kr/testing/trace_fin_semantics.py` — per-config semantic grounding of fin_c
  sub-terms vs GTs on the config semiautomaton (cover-aware), witness words,
  per-check subprocess cap (`KR_CHECK_TIMEOUT` 10s; verdicts OK/BAD/UNVERIFIED).
- `kr/testing/probe_reset_consistency.py` — checks every combined letter acts
  identity-or-reset per level under both context conventions (soundness
  precondition of the paper formulas; the Ga|Gb smoking gun).
- `kr/testing/probe_sgpdec_api.g` — hand-run GAP probe of the SgpDec calls
  used by the bridge (lift/π inversion, morphism property, closure).
- `kr/testing/ltl_diff.py` — containment direction + witness words.
- `kr/testing/test_kr_r4_audit.py` — structural checklist + drift grounding
  (gate for operator commits).
- `kr/testing/measure_formula_dag.py` — DAG vs string size of the assembled
  formula (unique nodes, unfolded tree, distinct temporal subformulas, build
  time); `--out` dumps the flat formula.
