# roundtrip — exploration status & handoff

A working note for an in-progress research direction. Read this first, then the
**algorithm/doc pointers** below — *not* the implementation — to get a clean formal
background before touching any code.

## The idea in one paragraph

A translator labels a **presentation**, not an abstract language: two automata for the
same ω-language can decompose completely differently, and our structural translators
(daisy, the decomp family) are presentation-sensitive by design. So the portfolio has
a second axis we had never named — not just *which translator*, but *which
presentation to hand it*. **Round-trip** is the first move on that axis: take a faithful
formula, re-describe the language by it (`Language.of_ltl`), and label the fresh
presentation again. It is soundness-free to do (the language is invariant) and it is
the **bridge from the systematic engine to the structural ones**: the bls cascade is
blind (it unrolls, ignoring structure), so its output, re-presented, *exposes*
structure that daisy then captures in closed form.

## The witness that started it

`genaut/corpus/2state1ap1acc/aut_33300.hoa` — a 2-state Büchi automaton whose initial
state has a non-self incoming edge, so it is **not** a daisy. The default recipe
floors on the cascade and returns a faithful but sprawling 31-node formula
(`technique: buchi`). Round-tripped through spot, the *same language* re-emerges as a
**1-weak** automaton, the daisy peel reads it off, and the result is `a & GFa` — 5
nodes, `technique: buchi+daisy+roundtrip`. The language was 1-weak-recognizable all
along; the input merely *presented* it as a genuine 2-state SCC.

## Formal background — read these (algorithm/contract docs, not code)

- `aut2ltl/roundtrip/algorithm.md` — **the construction**: seed → re-describe →
  relabel; two applications of one child; faithful-or-declines; the soundness chain.
  This is the spine.
- `aut2ltl/daisy/algorithm.md` — the exemplar peel (exact on the 1-weak fragment).
  Explains *why* a reshape that lands 1-weak is then read off in closed form.
- `aut2ltl/README.md` — the architecture: `Language → LTLResult = Translator`, the
  faithful-or-declines contract that makes translators compose soundly.
- `aut2ltl/result.py` (module docstring only) — the **accumulator idiom** and the
  two combine monoids (composition `credit`/`fuse`, choice `first`/`best_of`).
- `aut2ltl/portfolio/README.md` — the recipe system and the **brick algebra**:
  `first_success` (choice), `recurse` (self-reference), `best_of` (choice-by-size),
  `compose` (decorator `∘`). Says how a recipe is added (two lines).
- `aut2ltl/recurse/recurse.py` (docstring only) — the **strict-descent contract**.
  Load-bearing for why "iterate the round trip" is *not* a `recurse` (a reshape is
  not a strictly-smaller sub-problem).
- Root `README.md` — scope: sound, complete on the LTL fragment, and it *decides*
  LTL-definability. Background on what the tool is.

The implementations are tiny and should be opened only when editing:
`aut2ltl/roundtrip/roundtrip.py`, `aut2ltl/portfolio/recipes/roundtrip.py`,
`aut2ltl/portfolio/builder.py` (the `daisy_*` / `core` / `bls` blocks).

## The unification (motivation, paper-worthy)

Three capabilities are the *same machinery* (`Language.of_ltl(φ)` + reconstruction):
- **round-trip reconstruction** (formula → automaton → smaller formula),
- **LTL → LTL simplification** (an LTL normalizer via reconstruction),
- **PSL/SERE → LTL** (LTL when definable; a NOT_LTL *decision* when not — already
  works, since the CLI/`of_ltl` parse PSL and the portfolio decides definability).

## Current state (what is committed)

- `Roundtrip` translator (`aut2ltl/roundtrip/`) — the pure decorator, follows the
  result accumulator idiom, with `algorithm.md`. **Done.**
- Recipe `roundtrip` = `Simplify(Roundtrip(cakedsdet), "hi")`, registered for
  `--use roundtrip`. Top-level placement (reshapes the *whole* formula). Verified on
  the witness by hand (31→5). **Wired, not benchmarked.**
- `Language.of_ltl` now records `(definable=True, conclusive=True)` for a
  *syntactically LTL* formula (gated on `f.is_ltl_formula()`, so PSL stays undecided).
  Cheapens every relabel (skips the GAP aperiodicity oracle on a provably-definable
  reshape) and keeps the PSL→LTL path honest. **Done.**

**Not done:** gates not run, survey not run, **benchmark not run**, no measurement of
hit/regress rates, no `roundtrip_fine`, no `Memo`. The default recipe is unchanged
(`cakedsdet`); `roundtrip` is experimental.

## Open issues

- **Never-regress gap.** `Roundtrip` returns the relabel *unconditionally*. If a
  reshape is *less* exploitable, the relabel can be **larger** than the seed, so the
  shipped `roundtrip` recipe can regress. The fix is a `best_of`-from-outside that
  keeps the better of plain-vs-round-tripped — which is *why* `Memo` matters (below).
- **No translator-call memo.** `Language` interns and caches its representations and
  its definability verdict, but `T(L) → LTLResult` is **recomputed every call**
  (verified: the only memos in the tree are in the LTL/simplify layer). So
  `best_of([C, Roundtrip(C)])` would run `C(L)` twice (incumbent + seed) — wasteful,
  since the cascade/GAP is the expensive part.
- **Iterating is a new combinator, not `recurse`.** A presentation-search loop
  (round-trip, re-decompose, repeat) descends in a *size* measure, not a structural
  one — it is `best_of`-shaped (size-monotone, fixpoint stop), and needs the
  empirical **reshape-idempotence** question answered first (does
  `reshape(reshape(F)) ≈ reshape(F)`?). For now the round trip is **one-shot**.

## Current directions

1. **`roundtrip_fine` — the deep/surgical recipe.** Inject the round trip at the
   cascade floor instead of the top, so only a *stubborn residual* (the part the peels
   could not handle) is reshaped, not the whole formula. Design settled and built only
   from existing bricks:
   ```
   M     = daisy_trio_det( core(options) )        # a recurse closure, floors on bls — terminates
   floor = first_success([ PartScc(), Roundtrip(M) ])
   incumbent_rt = Simplify( compose(Strength, Acc, daisy_trio_det)(floor), "hi" )
   ```
   `M` is a *separate* recurse closure (not the enclosing leaf — that would loop, by
   recurse's descent contract). One round trip, terminates by construction. Open:
   `M` light (`daisy_trio_det(core)`) vs full (`cakedsdet`); start light.
2. **`Memo` — a peer Translator decorator.** `Memo(child)` memoizes `child(L)` keyed
   by `Language` (interned, so identity is a good key). Per-instance cache (share by
   referencing one `Memo` instance), placement-flexible. Decide: **share-on-hit**
   (relies on the read-only discipline of `credit`/`fuse`/`best_of`) vs
   **clone-on-hit** (defensive; needs a small `LTLResult.copy`). General perf win
   beyond round-trip.
3. **The combo recipe.** `best_of([ Memo(C), Roundtrip(Memo(C)) ])` — never-regress
   *and* a shared seed. The orthogonality is the point: `Roundtrip` stays pure (no
   size judgment), `best_of` is the choice, `Memo` is the only thing that knows about
   sharing. Three bricks, three concerns.
4. **Measure / probe (not started).** Per-corpus **improve / regress / no-change**
   rates, **split by seed technique** (buchi/weak/cobuchi/muller — the "maybe only
   buchi reshapes well" hypothesis is one pivot table); improvement magnitude; cost;
   **placement A/B** (top vs `roundtrip_fine` vs per-decomp-part); and the
   reshape-idempotence check that gates whether the iterating loop is worth building.
5. **Gates + benchmark.** Run `tests/bls/test_kr_r4_audit.py` (must be CLEAN) and
   `tests/survey.py` (must end SUCCESS); then the benchmark. None run yet for any
   roundtrip recipe.

## Disposition

Experimental. Default unchanged. The `of_ltl` definability patch is the only change
that touches a shared floor; it is committed but the gates have **not** been run on it
yet (do that before relying on it).
