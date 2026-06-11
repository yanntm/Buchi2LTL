# kr/ Current Status

Factual snapshot of the current state. History lives in `git log`; work items in
`kr/TODO.md`; doc map in `kr/README.md`.

## Pipeline (done, general)

- `decompose_aut`: Spot norm to det complete min-even parity with **state-based
  acceptance** (`sbacc` — soundness requirement: the Muller condition is lifted over
  configurations, so the infinitely-visited state set must determine acceptance)
  → generators (explicit 2^|AP| letters) → GAP/SgpDec holonomy → parsed `Cascade`.
- `Cascade`: levels, state↔config (1-based), letter valuations, `move_config`,
  Enter/Stay/Leave helpers, pruned config automaton, accepting configs.
- Good Muller sets: enumeration of strongly-connected **accepting subsets** of
  non-rejecting SCCs of the pruned config aut (`acc().accepting(in-M edge-mark union)`
  oracle, exact under sbacc; `KR_MULLER_SCC_LIMIT=12` gate, logged whole-SCC fallback).
- Stability: `bdd_utils` buddy-var precompute + per-case subprocess isolation in tests.

## Operators — now LITERAL paper forms (semantically validated; size blowup open)

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

## Semantic validation state (trace_fin_semantics grounding)

- **GFa: ALL SUB-TERMS GROUNDED OK** (1L regression green).
- **G(a -> X b): ALL SUB-TERMS GROUNDED OK** — every fin_c sub-term (r_to, r_gt0,
  r_with, fin, !fin) for every config is language-equivalent to ground truth.
  This was the first 2L target; the level recursion is now semantically right.

## Open problem: formula SIZE blowup (not non-termination)

Construction terminates (Fa: 24 reach calls, unchanged), but G(a->Xb)'s
assembled formula is ~3.2 MB (PAPER_MAX_LTL_SIZE). Spot translation of such
formulas (for equiv checks in audit/survey) is what stalls — use 10s timeouts
and treat TIMEOUT as a status. Root cause: operators round-trip STRINGS between
every call (`_str_f` → parse → simplify), so there is no DAG sharing — each
avoid conjunct physically copies the full nested tail σ∧Xτ, and `_str_f`
re-simplifies on every conversion. Fix plan in TODO P0-perf.

## Survey snapshot (pre-rewrite; re-run after the size fix)

1L cases all True; 2L ladder was failing for the now-fixed reasons; expect
G(a->Xb) (and likely others) to flip once equiv checks can run.

## Tooling for targeted work

- `kr/testing/survey_mp_cascade.py` — MP-class × depth ladder.
- `kr/testing/trace_fin_semantics.py` — per-config semantic grounding of fin_c
  sub-terms vs ground-truth automata, with witness words.
- `kr/testing/ltl_diff.py` — containment direction + witness words.
- `kr/testing/test_kr_r4_audit.py` — structural checklist + drift grounding
  (gate for operator commits).
