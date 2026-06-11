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

## Operators (done, general; multi-level precision in progress)

- The five reachability formulas, fully inductive for all depths (no 1L special
  cases): `reach_strong`/`reach_weak`, solid stay strong/weak + >0 variants,
  dashed change strong (incl. **s==t leave-and-return** + line(3) per the paper —
  the prose "(s≠t)" is motivation, not a guard). Base case (¬β)Uτ.
- `fin_c` per Lemma 7 with working ι==C postponement.
- Native spot.formula builders, memo + @lru_cache, early simplify, PAPER_* counters,
  `KR_TRACE=1` step tracing.
- Assembly: `reconstruct_ltl_paper_style` Muller DNF over good sets; specials for
  t/f/weak/looping; practical >3L guard.

## What roundtrips (Spot equiv True)

**All 1-level survey cases**: constants, Fa, Ga, G(a|b), G(a&Xa), F(a&b),
GFa, G(a->Fb), G(a|Fb) (recurrence), FGa, F(a&Gb) (persistence). Also 2L "a".
R4 audit fully CLEAN including the G(p|Fq) canary.

## What fails (all multi-level) — the current ladder, weakest MP class first

- safety: `G(a -> X b)` [2,2], `Ga | Gb` [1,4]
- guarantee: `a U b` [2,2] (recovers just "b"), `F(a & X b)` [2,2]
- obligation: `Fa | Gb`, `Fa & Gb`, `Ga | Fb` [2,2]
- 3L+: `Xa`, `a & Xa`, `GFa & GFb`, `FGa | FGb`, ... (some hit the >3L dev guard)

Known suspect divergences from the paper for the multi-level cases: R5 line(2)
iterates Enter(t) instead of Enter(b) with a non-paper shape; from-S lower-context
approximation of Enter/Leave/Stay at deeper levels. See TODO.

## Tooling for targeted work

- `kr/testing/survey_mp_cascade.py` — MP-class × depth ladder.
- `kr/testing/trace_fin_semantics.py` — per-config semantic grounding of fin_c
  sub-terms vs ground-truth automata, with witness words.
- `kr/testing/ltl_diff.py` — containment direction + witness words.
- `kr/testing/test_kr_r4_audit.py` — structural checklist + drift grounding
  (gate for operator commits).
