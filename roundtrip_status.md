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
6. **Exhaustive `genaut/corpus` sweep.** Run every roundtrip recipe (and the
   `cakedsdet` baseline) over the *entire* generated corpus — the exhaustive census of
   small automata under `genaut/corpus/` was built precisely for coverage and for
   surfacing nice examples. This is the real validation: the true improve / regress /
   no-change distribution, the size-gain histogram, fresh witnesses, and — important —
   the **outliers** where the minimal LTL stays large (candidate genuinely-complex /
   non-counter-free languages). Pair every run with a per-formula baseline so a
   regression is visible per case, not hidden in the aggregate.

## Why it matters — usage scenarios

If aut2ltl reliably returns *small* formulas (and it should, except where the language
is genuinely, humanly-incomprehensibly complex — such cases are real, but likely
outliers), the tool stops being a curiosity and becomes a spec-engineering instrument.
Humans author **reactive, simple, counter-free** properties — they think "after
request, eventually grant," not in terms of syntactic-monoid aperiodicity — and for
that vast, practically-dominant fragment a compact LTL formula *exists*; aut2ltl finds
it. Concretely: **recover a readable spec** from an automaton produced by learning,
synthesis, a runtime monitor, or a legacy SERE/regex ("what does this machine actually
require?"); **simplify/normalize** bloated LTL that arose from products, negations, or
compositional construction (an LTL *linter*); translate **PSL/SERE → LTL** when
possible and *decide* when not, for portability and tool interop; and read the
**not-LTL-definable verdict as design feedback** — it usually means a property
accidentally demands counting, a smell, since humans rarely intend that. LTL is a
remarkably compact notation for surprisingly rich languages, which is exactly why the
reverse direction — automaton back to a *small* formula — is valuable rather than
hopeless: for the languages people actually build, the small formula is out there, and
the round-trip insight (re-present, re-derive) is one of the levers that reaches it.

## Speculative directions (capture before context cools)

- **Complement round-trip — aut2ltl in the middle.** A language and its complement are
  two presentations of the same information, and one is often far cleaner: a safety
  property is an awkward `G`/`R` tangle whose complement is a crisp reachability daisy.
  So complement the automaton, reconstruct *that*, and negate —
  `best_of( reconstruct(L), ¬reconstruct(¬L) )`. Complementation is exponential and
  Spot avoids it, but this construction is already (triple-)exponential, so the cost is
  in budget — and the complement is frequently the *simpler side to peel*. A
  deliberately contrarian presentation move: we usually dodge complements; here we
  court them. (Original to this session — worth real attention.)
- **Syntactic LTL decomposition — a new decomposition brick.** When a seed comes back
  as `ψ1 ∧ … ∧ ψk` (the cascade and the acceptance split both do this), the `∧` is
  language *intersection* at the LTL level: each `ψi` is a separate, weaker constraint
  and `L(∧ψi) = ⋂ L(ψi)`. So re-derive each conjunct *independently*
  (`ψi' = reconstruct(L(ψi))`) and relink with `∧` — every subproblem is a strictly
  *simpler* language (smaller automaton, likelier to peel) than the whole, and the
  seed's own syntax handed us the split *for free*, a split the product automaton
  hides. Same for `∨` (union, as strength / SCC do). This is `roundtrip` fused with
  `decomp`, but the parts come from the *formula's boolean tree*, not from re-analyzing
  the automaton: read the seed's top `∧`/`∨`, reshape-and-re-derive each operand,
  recombine, recurse into operands that are themselves conjunctions/disjunctions. Sound
  trivially (`ψi' ≡ ψi`); and it generalizes *below* the top layer — in LTL, ω-language
  equivalence is a **congruence** (equivalence at position 0 entails equivalence at
  every suffix, since `w,i ⊨ φ ⇔ w[i:] ∈ L(φ)`), so *any* subformula may be swapped for
  an ω-equivalent reconstruction, the `∧`/`∨` seams being merely the highest-value
  cuts. It turns the cascade's ugly-but-*structured* output into leverage: the `∧` it
  emits is not noise, it is a decomposition certificate.
- **Presentation portfolio.** `best_of` over the *formula-mediated* presentation moves
  — plain reconstruction, the round trip, the complement round-trip, the syntactic
  split — letting each language be reached by whichever move peels it. (Pure
  automaton-level re-presentation is *not* a member: Spot's rewriting is already wired
  into `Language`, and standalone automaton heuristics were explored earlier and
  abandoned as ineffective.)
- **Reshape the *simplified* seed.** Re-present `simplify(seed)` rather than `seed`:
  our DAG-aware simplifier differs from Spot's, and a simpler formula may translate to
  a simpler automaton. A cheap knob.

## The wider frame — an algebra of translators, on benign reality

**It is not a portfolio; it is an algebra.** What this codebase has built is an
**algebra over translators**: sound translators (language-faithful-or-decline) as the
carrier, and the combinators as operations — `compose` (`∘`), `recurse` (fixpoint),
`first_success` / `best_of` (choice), and now the *moves* `roundtrip`, `complement`,
`syntactic-decompose`, `simplify`. Soundness is the **homomorphism property** — every
operation preserves the language — so the algebra is **closed**: any term over the
bricks is itself a sound translator, by construction. "Portfolio" undersells this. The
operational reading is a best-first **search over a rewrite graph** of equivalent
presentations for the size-minimal node (`best_of` is its greedy depth-1 case); the
structural reading is the algebra, and that is the one to claim. The empirical fact
that one move took 31→5 says the graph has **low diameter** from cascade-blob to
minimal — `translate` is a violent normalizer funnelling many formulas onto few
automata. Whether that low diameter holds broadly is *the* measurable hypothesis under
the whole approach.

**The algebra is, precisely, Kleene-shaped — with tests.** Map the bricks onto the
signature: `compose` is sequencing (`·`, unit `identity` = `1`); the two choices are
sums (`+`, unit `decline` = `0`) — `first_success` a *priority* sum (first
non-declined, left-biased), `best_of` a *size-ordered* sum; and `recurse` is the
least-fixpoint star (`*`). The moves (`roundtrip`, `complement`, `syntactic-decompose`,
`simplify`) are generators, and the predicates that gate them — `is_daisy`,
`is_ltl_formula`, the definability verdict — are **tests**: guards in the
Kleene-Algebra-with-Tests sense. The payoff is not aesthetic: if the recipe algebra is
(close to) a KAT, **recipe equivalence is decidable** and recipe terms **normalize** —
we could prove two recipes compute the same thing, and simplify a recipe expression
before ever running it. The tool minimizes formulas by a rewrite algebra; the recipes
themselves form a rewrite algebra we can minimize — inner and outer are the same kind
of object. (Caveat: the two-sum, two-sorted shape is not vanilla KA; which axioms hold,
and on which sort, is the open formalization.)

**Its laws are exactly our probes.** The identities we would most want —
`roundtrip ∘ roundtrip ≈ roundtrip` (reshape reaching a fixpoint),
`complement ∘ complement = id`, `simplify ∘ simplify = simplify`, `best_of(a, a) = a`,
the absorptions of `first_success` — are precisely the experiments already on the plan.
The measurement campaign is therefore not only benchmarking; it is **checking the
algebra's equational theory**. "Probe reshape-idempotence" *is* "establish the law that
makes `roundtrip` a well-behaved star-able operator." Science and engineering are the
same activity here.

**This is a proven design, not a flourish.** The operators-as-semantics-preserving-
homomorphisms discipline is imported deliberately from the author's prior
decision-diagram library, where the same algebra — sound operators, closed under
composition — delivered engineering robustness as much as elegance. That lineage is
*how this project got here*; the translator algebra meets the same criterion in every
useful way, and the bet is that it pays off the same way again.

**Worst case is mostly a stale worry on real inputs.** The construction is
(triple-)exponential and LTL-definability is hard — and it mostly does not matter,
because decomposition + round-trip **localize the expense to the largest irreducible
core**, the residual no structural move can simplify. Practical cost is governed by
*kernel size*, not input size (the "the hard part is small" phenomenon — treewidth,
parameterized kernels). Human specs *have* small kernels: people author reactive,
counter-free, compositional properties; they do not intend counting, the way Zeno
undecidability in timed systems is a modelling artefact, not a real requirement. The
analogy is SAT — worst-case intractable, random instances brutal, yet it *just works*
on human formulas because those are structured and benign. aut2ltl sits in the same
place: realistically useful on the inputs that occur, worst case notwithstanding. The
corpus sweep can make this concrete via the **kernel-size distribution**, expected
sharply peaked at small.

**The scientific output is the definability atlas, not only the formulas.** Deciding
LTL-definability over the exhaustive `genaut` census yields a map nobody has: the
smallest non-definable automata, the structural patterns that tip a language out of
LTL, definable-vs-not density as state/acceptance counts grow. The moves preserve
language, so they do not move the boundary — they let us reach the verdict cheaply and
at scale. The size wins sell the tool; this atlas is the contribution to the empirics
of where the LTL / ω-regular frontier actually lies, and the natural companion to the
corpus generation already underway.

**On confluence / scheduling — resolve it experimentally, do not theorize it.** The
moves are not independent (simplify can erase the `∧` seams syntactic-decompose needs;
order matters), so the rewrite system is not obviously confluent. This is a real but
*experimental* question: the goal is to *have the bricks* — composable, toggleable —
and let measurement pick the schedule, not to seek an analytic confluence proof.

**Exhaustive generation is the engine of discovery.** This whole direction began with
a single automaton from the exhaustive small-automata census whose cascade output was
ugly and whose round trip was tiny — the census *surfaced the witness*. The byproduct
of the sweep — `(automaton, smallest formula, winning move sequence)` triples — is
also, for free, a training set for a future learned dispatcher that predicts the first
move to try from shallow automaton features, bootstrapping the portfolio's intuition
from its own exhaustive play.

## The deep frame — recovering what automata destroy

LTL has a property automata do not: **compositional nesting**. Its meaning is built
from subformula meanings *at every position*, because `w,i ⊨ φ ⇔ w[i:] ∈ L(φ)` — so
ω-equivalence is a **congruence**, and a subformula may be replaced by an ω-equivalent
*anywhere* in the tree, soundly. An automaton flattens exactly this: determinization
and product braid every constraint into one monolithic transition structure and the
compositional seams vanish. **Recovering those seams is, in a real sense, the whole
problem** — automaton→LTL is hard precisely because the automaton has destroyed the
nesting LTL carries natively. Several directions below are the same move seen twice:
recover structure the automaton hid.

### Syntactic decomposition — exploit the nesting a *seed* still carries

The seed formula has not been flattened — it still wears its boolean tree. When the
cascade returns `ψ1 ∧ … ∧ ψk`, that tree is a **decomposition certificate**: the engine
has told us `L = ⋂ L(ψi)`, no automaton analysis needed. Three sources of leverage:

- *The split is handed to us, not searched.* `decomp` normally has to discover a split
  by analyzing SCCs / acceptance conjuncts; here we read the AST.
- *Isolation un-mixes the product.* Each `L(ψi) ⊇ L(φ)` is weaker, and `of_ltl(ψi)`
  builds a fresh automaton for that one constraint, free of the entanglement that
  braids the conjuncts together in `φ`'s automaton. That entanglement is exactly what
  blinds automaton-level decomp; cutting the syntactic `∧` un-braids it. So this is the
  formula-side **dual** of `AccDecompose` / `SccDecompose`, and it splits where they are
  blind.
- *It generalizes past `∧`/`∨`.* By the congruence above, *any* ugly sub-DAG (a nested
  `X(!a R Fa)` blob buried under a `U`) can be reconstructed in isolation and
  substituted. The boolean operands are merely the highest-value, most-independent cuts.

The pipeline is all bricks we have or are building: `split` (read the tree) →
`reconstruct` each operand (the recursive leaf — *cheap now*, since `of_ltl` tags each
sub-language definable and skips GAP) → `relink` with the same connective → `simplify`
(which may re-factor structure shared across the rebuilt operands) → recurse into
operands that are themselves `∧`/`∨`. It composes with `roundtrip` (each operand
reconstruction *is* a round trip) and lands as a new `decomp/` brick —
`SyntacticDecompose`, whose splitter is the formula, not the automaton. Open policy:
target by sub-DAG size (biggest blobs first) or top-layer-plus-one, and let `best_of`
keep the win; the cascade's top-level `∧` is the prime target, where ugliness and
structure coincide. Soundness caveat: future-time LTL only (our output) — not PSL with
past or SERE semantics.

## The kernel and its three certificates

Across the threads one object keeps returning: the **irreducible kernel** — the residual
that survives all structural peeling and falls to the cascade. It is at once the
complexity bottleneck (the only place the exponential is paid), the carrier of
non-definability (counting structure is exactly what cannot be peeled into compositional
LTL), and the locus of every diagnostic below. Three moves shrink, name, and quantify it.

**Shrink it — bidirectional peeling.** Daisy peels the *front* (clean local test: no
non-self incoming). The dual back-peel is harder *for a reason*: acceptance is a property
of infinite suffixes, so terminal structure is not disposable scaffolding — a terminal
SCC *is* the acceptance and must be labelled, not cut (that is `partscc`'s job). The
practical lever is to **widen the terminal catalog**: a **tail oracle** that, per state,
cheaply recognizes an LTL-trivial tail (`∅`, `Σω`, safety `G(B)`, guarantee `F(B)`,
persistence `FG`, recurrence `GF`, a one-step obligation) and marks it a leaf with a
known label, so the cascade never recurses past it; plus a **tail-language quotient**
(merge states with identical tail languages on the cascade's own generic-acceptance
form, where Spot's parity-minimization may not reach). Front peel + tail recognition =
the cascade sees only the irreducible *middle*. (Open: how to prune suffixes is not yet
solved — this is the current best handle.)

**Name it — the counting witness (a checkable SERE certificate).** Non-definability is
*not* witnessed by a single ω-word; the certificate is a **counting family**: a pumping
triple `(u, v, w)` and period `p > 1` such that `u·vⁿ·wω` flips membership in `L` as
`n mod p` — `L` distinguishes `vⁿ` by `n`, which counter-free LTL cannot. It is
extractable from the failing aperiodicity test (GAP's non-trivial subgroup gives the
period word `v`; the reaching states give `u`; the accepting tail gives `w`), and a SERE
expresses it compactly. Two payoffs: the NOT_LTL verdict becomes an **independently
checkable proof** (verify the alternation — `conclusive` becomes a witness, not a flag);
and at census scale the witnesses form a **field guide to non-LTL-ness** — the minimal
counting atoms, the periods that occur, how obstructions compose — the LTL/ω-regular
frontier drawn *with witnesses*, not only counts.

**Quantify it — the two-sided LTL bracket.** Decomposition yields sound one-sided LTL
bounds; take both at once — an under-approximation `B ⊆ L` (the LTL disjuncts of a
`∨`-split) and an over-approximation `A ⊇ L` (the LTL conjuncts of a `∧`-split) — so
`B ⊆ L ⊆ A`. Then `L` is LTL-definable **iff the bracket collapses** (`A = B`), and the
**bracket width is a quantitative distance-from-LTL**: not yes/no but *how much* escapes
LTL, and where (the gap `A ∖ B` is concentrated at the kernel, and the counting witness
lives inside it). The point-certificate (witness) and the set-certificate (bracket) are
the same frontier at two resolutions. Uses are immediate: `A` is a sound LTL **rejection
monitor** even when `L` is not LTL-monitorable; `B` is a sound **synthesis target**; and
the pair drives a structure-guided **abstraction-refinement** loop (peel more kernel,
tighten until they meet or stabilize on the non-LTL essence).

The keystone: the tool's deepest output is not the formula or the verdict but **the
kernel and its three certificates** — the LTL part (bracket), exactly why the rest is not
LTL (witness), and the smallest carrier of both the hardness and the non-definability
(the peeled kernel). A candidate spine for a second paper, distinct from the
size-reconstruction one.

## Approximation as abstract interpretation — the third pillar

The over/under-approximation bracket is far wider than non-LTL cleanup: it makes aut2ltl
an **abstract-interpreter of ω-regular languages into LTL**. Every move so far has been
language-*preserving* (a homomorphism); approximation is language-*inclusion*-preserving
(lax): `B ⊆ L ⊆ A`. And over/under are not separate knobs — they are the two **adjoints
of a Galois connection** between ω-regular and the LTL-definable sublattice (a Boolean
subalgebra, closed under ∩/∪/complement): `A` the upper adjoint (the "LTL hull"), `B`
the lower (the "LTL interior"), `[B, A]` the abstract element. The equivalence-preserving
rewrite algebra thus gains a **lax / adjoint layer**: the homomorphisms compute exact
reconstruction, the adjoints compute sound abstraction — one backbone, two regimes.

**Interpolant-shaped, with exactness as a dial.** A small over-approximation `A ⊇ L`,
over the same AP vocabulary, kept minimal by our size objective, *is* a temporal
interpolant / abstraction lemma (and the smallest LTL `A` with `L ⊆ A` and `A ∩ Bad = ∅`
is one in the literal sense). The move is to stop fixing exactness: `best_of` today
optimizes **size at fixed (exact) precision**; adding an **exactness axis** makes the
objective "smallest LTL within a tolerance, in a chosen direction" — the **precision
knob** of the abstraction. The two-sided bracket are the `ε = anything` extremes;
everything between trades tightness for compactness, which is exactly what a CEGAR-style
consumer wants — a coarse-but-small over-approximation, refined only if it proves too
coarse.

**Structure-guided refinement with a principled stop.** Classic CEGAR refines by
guessing predicates from a spurious counterexample; here refinement has a canonical
direction — **peel one more kernel layer exactly**, tightening `A` toward `L`. The
bracket narrows monotonically until it either closes (the property was LTL and is now
reconstructed) or stabilizes on the irreducible counting kernel — at which point the
**counting witness** proves no LTL abstraction can ever close it. Termination of the
abstraction-refinement *is* the non-definability certificate: the same kernel once more.
That is something predicate abstraction cannot offer — a principled stop *with a proof*.

**Fan-out.** A small over-approximation is a sound LTL **rejection monitor for a
necessary condition** of a complex/non-LTL property (cheap runtime checking of "at least
this must hold"); a small under-approximation is a sound **synthesis target** or a
strengthening lemma (a controller for `B` satisfies `L`); the dial itself is a
**specification compressor** — "the 10-symbol LTL closest to this 200-node exact one,"
lossy on purpose where the exact form is too big to read. Exact reconstruction is the
`ε = 0` corner of a much larger, more useful surface.

The wide statement: aut2ltl is not only an exact automaton→LTL reconstructor; it is an
**abstract-interpreter of ω-regular into LTL**, with exactness as one extreme of a
size↔precision dial, producing interpolants, monitors, synthesis targets, and lossy
compressions — the algebra absorbing it as a lax adjoint layer over the homomorphism
layer. A third pillar alongside reconstruction and the definability atlas.

## Concrete next steps

1. **Validate the floor patch.** Run `tests/bls/test_kr_r4_audit.py` (must be CLEAN)
   and `tests/survey.py` (must end SUCCESS) against the committed `of_ltl` change
   before relying on it — it is the only shared-floor edit so far.
2. **Build `Memo`** as a peer Translator decorator (per-instance, keyed by Language;
   decide share- vs clone-on-hit). The smallest, most reusable brick; it unblocks the
   combo.
3. **Build the never-regress combo recipe** `best_of([ Memo(C), Roundtrip(Memo(C)) ])`
   and `roundtrip_fine` (floor injection, light `M`). Both are two-line wirings.
4. **Exhaustive `genaut/corpus` sweep** of `cakedsdet` vs `roundtrip` vs
   `roundtrip_fine`, per-formula with baselines, then pivot improve / regress /
   no-change **by seed technique**. This answers "does it generalize, and to which
   families."
5. **Probe reshape-idempotence** on a sample (`reshape(reshape(F))` vs `reshape(F)`).
   Its answer decides whether the iterating presentation-search combinator
   (size-monotone, fixpoint stop — *not* `recurse`) is worth building.
6. Only then, if the data warrants, consider re-pointing the default.

## Disposition

Experimental. Default unchanged. The `of_ltl` definability patch is the only change
that touches a shared floor; it is committed but the gates have **not** been run on it
yet (do that before relying on it).

---

# Appendix A — the abstraction menu, in depth

Expansion of "Approximation as abstract interpretation." These are operators to
*build*, not ones in the tree today; what exists is the soundness substrate (the
algebra, faithful-or-declines). The one concrete contract change they all share:
`LTLResult` gains a **direction tag** — `exact | over | under` — plus an optional
tightness estimate, and `best_of` / `credit` must respect it (an `∧` of
over-approximations is an over-approximation; an `∨` of under-approximations is an
under-approximation; you may not credit a bound into a slot expecting exactness).
Given that tag, each abstraction below is just a translator returning a *tagged bound*
instead of an exact formula, and the algebra hosts it unchanged.

## Alphabet projection — predicate abstraction at the word level (ship this first)

Forget a subset of the atomic propositions. The over-approximation existentially
projects (`∃` the hidden APs): "the observable behaviour, ignoring the signals we chose
not to track"; the under-approximation universally projects (`∀`). This is textbook
predicate abstraction lifted to ω-words, with a *clean* Galois adjoint pair (projection
/ co-projection between the full- and sub-alphabet lattices). The win is large and
immediate: reconstruct over `{req, grant}` instead of eight signals and the formula
collapses, because most temporal tangle lives in the interaction of a few APs a reader
does not care about. Headline use: take a complex spec **as a HOA**, `∃`-project onto
the few signals of interest, reconstruct, and read off a small, sound,
*over-approximating* LTL — "ignoring the internals, here is what the interface must do."
Refinement is canonical: add one AP back. The first one to ship.

## The aperiodic quotient — abstracting away *exactly* the non-LTL-ness (the keystone)

Every ω-regular `L` has a **syntactic monoid**: words collapse into classes where
`u ≡ v` iff interchangeable in every context (`∀ x,y: xuy ∈ L ⇔ xvy ∈ L`); the classes
under concatenation form a finite monoid, the algebraic fingerprint of `L` — the same
substrate the cascade is built on. The theorem that *is* this project: **`L` is
LTL-definable iff its syntactic monoid is aperiodic** (counter-free) — iff it contains
**no non-trivial group**. A group inside the monoid is an element `g` with period
`p > 1` (`g, g², …, gᵖ = 1` cycling): the language can tell `gⁿ` apart by `n mod p` —
it *counts*, the one thing LTL cannot do.

Concretely: `L =` "an **even** number of `a`s before the first `b`, then anything." The
letter `a` is a **toggle** flipping even↔odd, so the monoid carries a two-element group
`{even, odd} ≅ ℤ/2`. *That group is the sole reason `L` is not LTL* — everything else is
aperiodic; the parity counter is the lone obstruction.

The abstraction is the canonical algebraic move: **quotient the monoid to kill the
group.** Take the largest *aperiodic* quotient — the surjective morphism collapsing each
group to a point (identify `g` with `g²` with `1`, destroying the period). Collapsing the
`ℤ/2`, "even" and "odd" merge into one class: the abstracted monoid *cannot see parity*,
is aperiodic, and so its language is LTL-definable. Round the acceptance *up* to whole
collapsed classes → the **over-approximation** "**some** number of `a`s then `b`" (both
parities admitted, `⊇ L`); round *down* → the **under-approximation**. The thing
collapsed — the toggle group — is **precisely the counting witness**: extract the
subgroup and it is your witness; collapse the subgroup and it is your abstraction. One
object, residual vs. production.

And it is mechanizable from what `bls` already computes. **Krohn–Rhodes separates the
group factors from the aperiodic ones** — that is the holonomy decomposition. LTL ⇔ every
cascade factor aperiodic. Today, meeting a group factor, `bls` concludes NOT_LTL and
stops; the abstraction is one step further — **collapse each group factor to its
aperiodic image** (group → reset), rebuild the cascade, and out comes a sound LTL formula
approximating `L`, the rounding choosing over vs. under, the collapsed factor returned as
the witness. So the most principled LTL abstraction is "drop the group factors of the
Krohn–Rhodes cascade we already build," and it abstracts away *only* the non-LTL-ness —
nothing aperiodic is touched. No other abstraction on the menu has that alignment with
the boundary.

## Acceptance-class weakening — abstract into the tool's sweet spot

The chain `Ga ⟹ FGa ⟹ GFa` (always → eventually-always → infinitely-often) orders the
strengths: `Ga` *under*-approximates `GFa`, `GFa` *over*-approximates `Ga`. Acceptance
weakening moves along it — snap a Rabin/Muller condition *up* to a Büchi `GF` (over) or
*down* to coBüchi `FG` / weak (under). Its force is structural: the **weak / Büchi /
coBüchi classes are exactly where the peels and daisy already fire effortlessly**, so
this abstraction lands its output *in the tool's sweet spot* rather than in a vacuum. One
acceptance transform in, an easy reconstruction out. Ranks just behind the aperiodic
quotient, because its landing zone is the fragment we are strongest on.

## Assume-guarantee — temporal `restrict`/`constrain` (Coudert–Madre lifted)

Given an environment assumption `E`, reconstruct `L` *only where `E` holds*: find the
smallest LTL `φ` that **agrees with `L` on `E`** (`L(φ) ∩ E = L ∩ E`), free off `E`.
This is exactly BDD minimization with **don't-cares**, `restrict` / `constrain` (the
generalized cofactor), lifted to temporal logic: `E` is the **care-set**, `¬E` the
don't-care region and thus *simplification fuel* — every behaviour the environment never
produces is a degree of freedom to shrink the formula.

Is that the same as AND-ing the care onto the system? **No — and the difference is the
point.** `L ∧ E` (system restricted to `E`) and `L ∨ ¬E` (vacuously true off `E`) are the
**two endpoints** of the admissible interval `[L ∩ E, L ∪ ¬E]`: the smallest and largest
*languages* agreeing with `L` on `E`. Both are valid completions, but their *formulas*
may be large and you have committed a value off `E`. `restrict` is free to pick **any**
member of that interval to **minimise formula size** — it need equal neither endpoint; it
spends the don't-cares to be smaller than both. So AND-ing throws the freedom away by
fixing the off-`E` value; the cofactor keeps it and optimises (`best_of` over the
interval *is* that search, the direction tag fixing which corner). It is also the most
*practically* requested form — nobody specifies over all of `Σω`; they specify under a
contract — and the don't-care interval is usually exactly where the size collapses.

## Galois connections — met for the structured domains, one honest caveat

For the **named** domains the conditions hold cleanly: alphabet projection (`∃` and its
co-projection, a genuine adjoint), the safety / topological closure (closure / interior,
a *unique* hull), and the aperiodic quotient (the canonical largest-aperiodic morphism).
For the **general** "smallest LTL formula `⊇ L`," the caveat: LTL-definable languages are
closed under *finite* Boolean operations but **not** under arbitrary intersection, so
there need be **no unique least** LTL over-approximation — two incomparable minimal hulls
can exist. There the adjoint is not a function and "Galois connection" softens to
"best-effort bound found by search" (`best_of`, direction-tagged). Abstract
interpretation has always lived with non-unique best abstractions; that is what widening
is for. So: immediate for projection / closure / quotient; subtle (uniqueness fails) for
the unstructured hull.

## Covered, and parked

- **Manna–Pnueli hierarchy (the class lattice).** Covered, not a new lever: the hierarchy
  is a fact about *which fragment a method handles*, already exploited by the decomp
  family (and the sketched syntactic decompositions). We are complete regardless, via
  `bls`; the goal is intelligible formulas, not more coverage.
- **Bounded horizon / LTL_f / finite-star.** Parked. A finite-star (LTL_f) generator may
  be useful but currently raises more than it answers; revisit only if SERE→LTL matures
  into a real path.

## The percolation, restated

The abstraction layer and the diagnostic layer are one structure. The aperiodic quotient
(the best LTL over-approximation) collapses *the same subgroup* the certificate extracts
as a witness; the safety closure is the topological hull; the bracket gap is the kernel.
Build two things — the `LTLResult` direction tag and the aperiodic-quotient operator (a
modification of the cascade `bls` already produces) — and the seed of the whole
abstract-interpreter is in hand, sharing the kernel with everything else in this document.

---

# Appendix B — aut2ltl as a certifying LTL learner

Consigns two conversation posts on the "synthesize LTL from scenarios" community.
Sound-looking directions, **not yet vetted against that literature** — flagged for
later decompression by someone who knows the domain.

## Where the field sits, and the one caveat that places us

LTL-from-scenarios splits into two poles. **SAT/SMT-minimal learners** (Neider–Gavran
"Learning LTL" and descendants) encode "∃ an LTL formula of size ≤ n consistent with
this sample of positive/negative ultimately-periodic traces" and minimize `n` — exact,
Occam-optimal, but they avoid automata *precisely because automaton→LTL was the hard
part*, and they scale poorly. **Template/mining learners** (Texada, Perracotta,
Dwyer-pattern miners) instantiate known patterns against logs — scalable and legible,
but boxed into a template catalog. The field is thus "exact-but-small-and-cryptic" vs
"scalable-and-readable-but-template-bound."

The placing caveat, stated honestly: **a finite sample is always LTL-consistent** (any
two distinct ω-words differ at some position `i`, and `Xⁱ(a)` separates them). So our
headline "decide non-LTL + emit a witness" does **not** apply to raw finite-sample
consistency. It bites in the mode where the object is a *language / model* — learning
the LTL of an inferred or given automaton — a real and common regime (spec mining from
models, RPNI / L*-learned automata, synthesized controllers).

## What we bring — five differentiators (most-novel last)

1. **The missing back-end: automaton → small, legible LTL.** State-merging / RPNI /
   Büchi-learning produce *automata*; the community wants *formulas*; that conversion
   is the gap the SAT learners route around and is our entire purpose. aut2ltl is a
   drop-in back-end for any automaton-learner — learn the automaton (often far more
   scalable than SAT-LTL on large samples), then we reconstruct the small LTL.
   Re-legitimizes the automaton-learning route the field abandoned.
2. **A *certifying* learner — it knows when to stop trying LTL.** In the language/model
   mode, when the target is non-LTL, existing learners just grow the bound and cannot
   tell "need a bigger formula" from "no LTL exists." We decide it (aperiodicity) and
   return the counting witness `u·vⁿ·wω` — a checkable proof of impossibility. A
   learner that *certifies impossibility* rather than failing silently appears new here.
3. **The LTL bracket as version space + approximate learning.** (Developed below.)
4. **Legibility as the objective, via patterns — not minimal size.** Bias the pluggable
   `best_of` comparator toward Dwyer-pattern shapes, so the learned spec reads
   `response(req,grant) ∧ absence(error after reset)` rather than a minimal-but-cryptic
   blob. Template-*aware* (legible) without being template-*bound* (still complete via
   `bls`) — a third position between the poles.
5. **The witness as a *reformulation* guide (the freshest).** When the target is
   non-LTL because of a counter, the witness names *which* counter, so aut2ltl can say
   "not LTL over your signals, but it becomes LTL if you add one observable tracking
   `parity-of-a` — here is the formula over the enriched alphabet." Alphabet projection
   run in reverse: an impossibility result turned into actionable **spec repair**. No
   learner offers "here is the one extra variable that fixes it."

## The precise spine of #3: learning = temporal `restrict` over a sampled don't-care set

A sample `(P, N)` partitions `Σω` into **on-set `P`** (must accept), **off-set `N`**
(must reject), and **don't-care `U = Σω \ (P ∪ N)`** (everything unseen) — an
*incompletely-specified* ω-language. "Smallest LTL agreeing with the spec on `P ∪ N`,
free on `U`" is two-level / cofactor minimization with don't-cares — the **temporal
`restrict` of Appendix A's assume-guarantee**, with the care-set being "the seen words"
instead of "the assumption." So **learning and assume-guarantee are the same operator**,
two readings of the care-set; the don't-care freedom (unseen words) is the
generalization power, and minimizing formula size over it is Occam, mechanized. No new
machinery — the restrict operator pointed at a sampled care-set.

**Version space = the bracket; its width is a query oracle.** Mitchell's
concept-learning boundaries land in our terms: the under-approximation `B`
(most-specific consistent: smallest LTL covering `P`, avoiding `N`), the
over-approximation `A` (most-general: largest LTL avoiding `N`), and `[B, A]` is the
version space — every sample-consistent LTL lives between them. Bracket width is a
**sufficiency signal** (wide ⇒ the sample under-constrains; narrow ⇒ it nearly
determines the formula), and the gap `A ∖ B` is exactly the words the sample has not
pinned — so **the most informative active query is any word in `A ∖ B`**: ask "accept
`w`?" and provably cut the version space. Active-learning query selection becomes
"sample the bracket gap," not a heuristic.

**Abstraction domains = declarative generalization biases.** A learner needs an
inductive bias; each abstraction domain is one, by intersecting the version space with a
sub-lattice: "simplest *safety* property consistent" = version space ∩ safety
sublattice; "*bounded-horizon*" = ∩ depth-≤`k`; "over *these signals only*" = alphabet
projection of the bracket; "as a *Dwyer pattern*" = ∩ the pattern sublattice (legible by
construction). Declarative, lattice-defined biases instead of an opaque size prior — a
genuinely new knob for the community.

**The lossy dial is noise tolerance.** Allow a budget of misclassifications: let the
smallest formula absorb a few stubborn points into the don't-care set (treat outliers
as unseen). "Smallest LTL consistent with ≥ 95% of the sample" is regularized cofactor
minimization — the size↔accuracy dial is the regularization strength. Soft / noisy
learning is a precision *setting*, not a separate algorithm. (This corrects the earlier
"not noise-tolerant" scoping.)

**Convergence measures definability.** If the target `L` is LTL and the sample grows
toward a characteristic sample, the version space `[B, A]` **collapses to `{L}`**
(modulo equivalence) — bracket-width → 0 *is* identification-in-the-limit, a clean stop.
If `L` is non-LTL, the bracket **never collapses**; it stabilizes at a residual gap, and
that gap *is the non-LTL kernel*, its counting witness sitting in the leftover `A ∖ B`.
Collapse ⇒ learned and LTL; stable gap ⇒ non-LTL — the learner's convergence behaviour
literally decides definability.

## Honest scope and soft spots

- Not **end-to-end** from raw traces — we need an automaton / language as input, so we
  are a back-end (pair with an ω-automaton learner for the full pipeline).
- Not natively **active** (the bracket-gap query loop is the *path* to it, not a built
  feature), and the certification / convergence differentiators (#2, #5) fire only in
  the language/model regime, not raw finite-sample consistency.
- Computing genuinely-extremal `B` / `A` in the LTL lattice is neither unique nor cheap
  (the Galois uniqueness caveat), so in practice the version space is *approximated* by
  our reconstruction bounds — fine for the active loop and the biases, not a tight
  theoretical version space. Be candid about this in any write-up.

## One experiment to back it

Take a published LTL-learning benchmark, learn an automaton with an off-the-shelf
method, run aut2ltl as the back-end, and compare (a) formula size / legibility vs the
SAT-minimal learners, (b) the cases where we *certify* non-LTL that they can only fail
on, (c) the reformulation suggestions.
