# memo.md — plan: make `deep_nobls_memo` actually save calls

Untracked scratch handoff. Goal of this thread: the shared-store `Memo` op-cache
*should* save a massive number of calls, but the survey is **perf-flat** — so the
cache is not doing its job. This file is a ready-to-execute plan for a fresh session.

## What already landed (committed, on master)
- `297b6d7c` **memo brick**: `Memo` cache keyed on `(operation, Language)` where
  operation = `id(child)`; optional shared `store` via `Memo.new_store()`; store is a
  two-level `WeakKeyDictionary[Language, {op-id: result}]`. Default store is
  per-instance (so `roundtrip_best`'s `best_of([m, Roundtrip(m)])` is unchanged).
  API: `Memo(child, *, name="memo", store=None)`, `Memo.new_store()`.
  File: `aut2ltl/combinators/memo/memo.py` (+ README.md/algorithm.md/__init__.py docs).
- `2deaab3e` **recipe**: `deep_nobls_memo` threads one `store` through the *arm*
  (`_nobls_memo`) — every arm primitive/stage/simplifier wrapped on it. Seed + final
  simplify also wrapped, but only at top level.
- `ecf6707b` **TODO**: the instrument/diagnose entry + the seed-gap suspect.

## The core finding (why it's flat)
`deep_nobls_memo` depth-caches only the **arm**. The forward **seed** is
`m(cakedsdet(options))` — the *whole* cakedsdet recipe wrapped in ONE `Memo`, so only
its outermost `(id, top-language)` call is cached, and `as_translator` calls the seed
**once** per top language → that entry is written once, never reused = useless.
cakedsdet's internal peel/decompose/**bls-cascade** work (the expensive part, and where
the r3 / `_07` cost lives) is on **no** shared store, and cannot share with the arm's
re-presentation of the same sub-languages (different, uncached instances).

Evidence: `deep_nobls_memo` is output-identical to `deep_nobls` with build time within
±2% on all three corpora (`logs/opcache2/`, `logs/opcache/`). The spotrun-limit boost
(`KR_TRANSLATE_INPROC_TREE_LIMIT=300 KR_TRANSLATE_TREE_LIMIT=3000`) was ALSO a null
result on all corpora (`logs/spotboost/`) — towers did not collapse at 3k.

## The plan (user's directive)
**Inline every recipe `deep_nobls_memo` calls, transitively, into the recipe file;
drop the imports; then dress each inlined op with the shared `store`.** It is too
intrusive to retrofit the memo onto the shared builder/recipes just to test — so we
inline a fat, self-contained `deep_nobls_memo.py`, prove the win (or not), and only
then consider retrofitting. Keep it readable by **passing the memo store (or the
`m`/`md` lifts) as an argument** to the inlined helper signatures.

Concretely: build the seed `cakedsdet` from the SAME `store`-wrapped primitives the arm
uses, so a sub-language peeled while seeding is cached and reused when the round trip
re-presents that node (and vice versa). That cross-engine sharing is the whole point —
it cannot happen today because seed and arm use different, unwrapped instances.

### Inline dependency tree (what to copy in, all the way down)
`deep_nobls_memo` calls:
- `cakedsdet(options)` — INLINE. Its body (from `recipes/cakedsdet.py`):
  ```python
  incumbent = Simplify(compose(StrengthDecompose, AccDecompose, daisy_trio_det)(core(options)), "hi")
  rich      = Simplify(compose(Invariant, StrengthDecompose, SccDecompose,
                               Invariant, AccDecompose, daisy_trio_det_inv)(PartScc()), "hi")
  return best_of([incumbent, rich], name="cakedsdet",
                 beats=significantly_smaller(rel=0.25, floor=2))
  ```
  Needs: `best_of, significantly_smaller` (combinators.best_of), `compose`
  (combinators.compose), `PartScc`, `AccDecompose/StrengthDecompose/SccDecompose/
  Invariant` (decomp.*), `Simplify` (simplify_ltl), and the builder blocks
  `daisy_trio_det`, `daisy_trio_det_inv`, `core`.
- `nobls(options)` — already inlined as `_nobls_memo` (keep as the template).

Builder blocks to inline (from `portfolio/builder.py`; all `recurse`-tied):
- `core(options)` = `first_success([PartScc(), bls(options)], name="core")`.
- `bls(options)` = `definability_gate(as_translator(make_hierarchy_class(options)))`
  (imports: `aut2ltl.bls.aut2cas.as_translator` — NOTE name clash with
  `ltl_rewriter.as_translator` already imported in the recipe; alias one, e.g.
  `from aut2ltl.bls.aut2cas import as_translator as bls_as_translator`).
  `definability_gate` (aut2ltl.bls.definability), `make_hierarchy_class`
  (aut2ltl.bls.hierarchy_class).
- `daisy_trio_det(child)` =
  ```python
  recurse(lambda leaf: first_success(
      [Daisy(leaf), Daisy2(leaf), DaisystarDet(leaf), Daisystar(leaf), child],
      name="daisy_trio_det"))
  ```
- `daisy_trio_det_inv(child)` = same but wrapped in `Invariant(first_success([...]))`
  inside the `recurse` lambda (invariant woven per descent).
- `recurse` (combinators.recurse), `first_success` (combinators.first_success),
  `compose` (combinators.compose) — import as combinators, don't inline (they're
  primitive bricks, not recipes).

Primitive translators (import, don't inline — leaves): `Daisy, Daisy2, Daisystar,
DaisystarDet, PartScc, Invariant, AccDecompose, SccDecompose, StrengthDecompose,
Simplify`. These are the ops we WRAP with `m(...)`.

### Wiring the memo (readability)
Make one `store = Memo.new_store()` at the top of `deep_nobls_memo`, define
`m = lambda c: Memo(c, store=store)` and `md = lambda dec: (lambda c: m(dec(c)))`, and
**pass `m`/`md` (or `store`) into each inlined builder helper** so the assembly reads
close to the originals:
```python
def _core(options, m):           return first_success([m(PartScc()), m(_bls(options, m))], name="core")
def _daisy_trio_det(child, m):   ...first_success([m(Daisy(leaf)), m(Daisy2(leaf)), ...], name=...)
```
Wrap the recurse leaf/fixpoint in `m` exactly as `_nobls_memo` wraps `holder["daisy"]`
(the recursion target must be memoized so a re-reached suffix is a hit — see the
`holder`/`daisy_leaf` hand-tied knot in the current `_nobls_memo`).

Key soundness note carried over: wrapping is output-neutral (`Memo` is identity on
results); with `(op, Language)` keying no stage shadows another, so cross-engine sharing
via one store is safe. Verify output stays == `deep_nobls` after inlining.

## How to test / measure (per repo discipline; ≤15s per example)
1. Correctness gate: `python3 -m survey --folder samples/validation --logs logs/rerun/x`
   must end `SUCCESS`.
2. Size/time vs default: run kinska + benchmark into a NEW `logs/<tag>/` folder (never
   rm existing logs — user preference), diff with
   `python3 -m survey.diff.results results/reference/<corpus>/*.csv logs/<tag>/.../survey_*.csv`.
   Watch: DAG delta and timeout count.
3. **Instrument the memo** (the actual diagnosis). Copy the pattern of
   `tests/probes/gate_count.py` (it monkeypatches, builds via
   `build_portfolio(Options.from_specs(ALL_SPECS), [use])`, drives ONE HOA in-process,
   writes `tests/probes/logs/`). Write `tests/probes/memo_count.py`: subclass `Memo`
   with class-level hit/miss/insert counters, monkeypatch
   `aut2ltl.portfolio.recipes.deep_nobls_memo.Memo` to the subclass BEFORE building the
   translator, run on kinska `counting_buchi_1ap_18` (the `gate_count` motivation:
   1271 gate calls / 78 distinct → 94% recomputes, one suffix ×240). Report hits vs
   misses per op and total. Near-zero hits after inlining ⇒ redundancy isn't at this
   granularity; high hits + smaller DAG ⇒ the inlining worked, consider retrofit.
   Single-input invoke: `python3 tests/probes/memo_count.py <path.hoa>`.
   Good tower inputs: `samples/kinska/counting/1ap/counting_buchi_1ap_18.txt`, or the
   `_07` that blows up (`counting_buchi_1ap_07.txt`, ~90s raw — cap it).

## Expected outcome / open hypotheses
- If cross-engine (seed↔arm) sharing fires: DAG should drop where the seed and round
  trip touch the same büchi-tower suffixes, and build time should fall (bls cascade +
  r3 simplify computed once per language, not per descent path). This is the win the
  user is confident exists ("buchi towers *can* collapse if we try").
- If still flat after full inlining + instrumentation shows low hit rate: the
  redundancy the memo targets isn't at the `(op, language)` granularity — reconsider
  what to key on (maybe (op, language) is too fine because languages differ per node;
  the `gate_count` redundancy is on `(input-aut, candidate)` PAIRS, which is a
  different key than the node language). This mismatch is worth checking early: the
  gate probe counts redundancy on candidate pairs, but `Memo` keys on the node
  language — they may not coincide.

## Files in play
- `aut2ltl/portfolio/recipes/deep_nobls_memo.py` — the fat recipe to grow.
- `aut2ltl/portfolio/recipes/cakedsdet.py`, `nobls.py` — inline sources.
- `aut2ltl/portfolio/builder.py` — `bls/core/daisy_trio_det/daisy_trio_det_inv` sources.
- `aut2ltl/combinators/memo/memo.py` — the `Memo` brick (store API).
- `tests/probes/gate_count.py` — probe pattern to copy for `memo_count.py`.
- Result scratch: `logs/opcache2/` (super-memo), `logs/spotboost/` (null spot boost),
  `results/reference/` (committed baselines to diff against).
