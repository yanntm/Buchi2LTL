# Symbolic DAG representation & folding — working notes

Status: **research direction, not concluded.** This document stores our
current understanding of WHY the FoSSaCS'22 construction explodes in
practice, the measurements that support that reading, and the candidate
counter-measures. Sections marked **OPEN** are unresolved on purpose.
Current implementation state: `kr/STATUS.md`; work queue: `kr/TODO.md`.

## Thesis

The double-exponential of the paper prices the output formula as a **tree**.
The construction as implemented produces a hash-consed **DAG**, and on every
case measured so far the DAG stays small and cheap while only its unfolding
(tree / flat string) explodes. If that observation survives folding and
larger benchmarks, the practical complexity of automata→LTL via cascades is
governed by the DAG, and the paper bound is a statement about an artifact —
the insistence on flat rendering.

## Measurements (2026-06-11 session, true-cascade pipeline)

| case | aut | cascade | build | DAG nodes | unfolded tree | sharing | distinct temporal |
|---|---|---|---|---|---|---|---|
| `G(a->Xb)` | 3 st | 2L [2,2] | 0.08s | 1,173 | ~1.5M | 1,270x | 192 |
| `Ga\|Gb` | 4 st | 2L [4,3] | 0.08s | 988 | 2.0M | 2,044x | 191 |
| `G(p->(qUr))` | 3 st | 2L [2,2], 8 letters | 0.14s | 9,024 | 64.8M | 7,179x | 4,115 |
| `XXXa` | 6 st | 5L [2,2,2,2,2] | 0.18s | 4,948 | 72.0M | 14,559x | 1,076 |
| `(a U b)\|Gc` | — | 3L [2,4,3], 8 letters | 9.5s | (284,608 distinct subproblems) | — | — | — |

Corroborating facts:

- **Construction is never the wall.** All of the above build in ≤10s; the
  five ladder failures labeled CONSTRUCT_TIMEOUT are dominated by the final
  flat `str()` of the result, not by the recursion (e.g. `(a U b)|Gc`:
  9.5s build, serialization blows a 30s budget; one `G(p->(qUr))` fin
  sub-term flattens to 108MB).
- **Sharing compounds with depth and alphabet** (1,270x at 2L/2AP →
  7,179x at 2L/3AP → 14,559x at 5L) — exactly the multiplicative growth the
  bound predicts, and it lands entirely in the unfolding.
- **Memoization is load-bearing.** Before the helper memo, `(a U b)|Gc`
  showed 437k raw reach calls at 91.5% cache-hit rate without finishing;
  with one-expansion-per-distinct-subproblem it completes (284k distinct).
  The subproblem space IS the b^k tail space (see below) — finite, but only
  traversable once each.
- **External rewriting does not help and can't be waited on.** Spot's
  `tl_simplifier` is not sharing-aware; it stalled >10s inside C++ on
  formulas under 2,000 unfolded nodes (watchdog-confirmed). It is out of the
  construction path by policy; this also means *nothing currently folds
  vacuous structure* — the numbers above are raw.
- **Semantics are not in question.** MP ladder: 21 equiv=True (through 4
  levels: `XXa`), zero equiv=FALSE; cover-aware grounding: zero
  contradictions at every depth probed (incl. `XXXa`, `X(a&Xa)` at 5L).
- **Known irreducible answers exist for the X-ladder.** The shape-based
  heuristic (`buchi2ltl/`, `sl` technique) returns `X(X(X(a & XG(1))))` for
  `XXXa` — ~5 tokens. The kr/ construction needs 4,948 DAG nodes for the
  same language. The gap is foldable structure, not information.

## Why it explodes (mechanics, condensed)

The construction speaks one cascade level at a time. Three multiplicative
mechanisms stack:

1. **Tail wrapping.** When level l delegates "reach the firing context" to
   level l+1, the target obligation is wrapped: τ → σ ∧ Xτ, one variant per
   candidate letter σ. Distinct tails ⇒ distinct subproblems ⇒ ~b^k nested
   tail combinations after k levels (b = combined letters per level). This
   is the exponential-in-depth, purest on the X-ladder where each X is one
   level (the cascade is a shift register).
2. **Avoid-conjuncts.** "Stay in s until σ fires" is expressed as one
   recursive reach per leave-letter η ("η does not fire first"), each with
   its own wrapped tail. Directions that spell out, at every junction, the
   full directions for every wrong turn — recursively.
3. **Fin/Muller fan-out.** Acceptance is a DNF over candidate inf-sets M;
   each term conjoins fin(C)/¬fin(C) for EVERY config C, each fin a full
   reach construction.

Hash-consing merges identical recitations, which is why the DAG is 10³–10⁴
nodes where the tree is 10⁶–10⁸. The residual DAG bloat (4,948 vs ~5 for
`XXXa`) is structure the construction emits but cannot see is vacuous:
unreachable firing contexts, avoid-conjuncts over letters that cannot occur
there, tails through dead configs, time-shifted copies of the same
obligation.

## The BDD analogy — what we have, what we lack

| BDD ingredient | our status |
|---|---|
| unique table (node sharing) | HAVE — spot.formula hash-consing |
| computed table (memo) | HAVE — reach lru + helper memo, one expansion per distinct subproblem |
| reduction rules (local canonicalization) | **LACK** — nothing folds since tl_simplifier left the path; only constructor-level constant folding |
| canonical form ⇒ equivalence = pointer equality | **UNREACHABLE in full** — LTL language equivalence is PSPACE-complete, no cheap per-node canonicity exists. Approximations only. |

## Candidate counter-measures (with expected effect)

Ordered; none implemented yet. Success metric throughout: DAG nodes and
distinct temporal subterms on the X-ladder falling from thousands toward
O(depth), with ladder equiv/groundings unchanged.

1. **Object-out API (plumbing, first).** `reconstruct` hands out the
   `spot.formula` object; `str()` on demand only. No semantic effect;
   converts the 7 serialization-bound CONSTRUCT_TIMEOUTs into measurable
   outputs and gives any analysis layer its native input.
2. **Cascade-aware vacuity pruning, during construction.** The builder can
   consult the config graph: drop avoid-conjuncts for letters that cannot
   occur from the relevant contexts, disjuncts whose firing context is
   unreachable, empty Enter/Stay cases. Prunes *memo keys*, so fewer
   subproblems are ever expanded — attacks b^k at its base. Expected to be
   the largest single win on the X-ladder (one live path through the shift
   register).
3. **Own sharing-aware fold pass.** Bottom-up over unique nodes (memoized by
   id, O(DAG) not O(tree)): absorption, X-pulling where it merges tails,
   dead-branch elimination using facts from (2). This is the "reduce" step
   of the BDD analogy, done by us because no external tool walks DAGs.
4. **Budgeted semantic interning.** For subterms under a size cap, decide
   language equality (Spot, subprocess, ≤10s budget per our external-call
   policy) and merge equivalence classes to one representative. Collapses
   the time-shifted-variant axis (`XXXa`'s 1,076 distinct temporal subterms
   are largely the same obligation at different delays). Directly targets
   the 32-acc-set verification wall.

## Letter fusion (counter-measure B, ACTIVE 2026-06-12)

User-proposed, validated direction: **equivalence classes of futures over the
2^|AP| letters**. Inspection of the five enumeration sites
(`last_steps`/`leave_s`/`bad_pre` in solid⁺/wsolid⁺, `enter_t`/`enter_b`/
line-3 `leave_s` in dashed) shows the summand depends on the concrete letter
ONLY through its guard — the structure is fixed by the rest of the dedupe
key. So fusion is: drop `li` from the existing `_dedupe` key, OR the guards
of the group, emit the OR minimized via BDD + Minato ISOP
(`spot.formula_to_bdd`/`bdd_to_formula`, verified in `probe_guard_fusion`).
`enter_t`/`enter_b` additionally key on the arrival config (their inner
solid reads it).

Why it attacks the explosion at the root: each per-letter disjunct mints its
own tail `σᵢ ∧ Xτ`; the distinct-tail population is the measured driver
(probe_tail_anatomy: ×2–10 per level). Fusion mints ONE tail
`(σ₁∨…∨σₘ) ∧ Xτ` per outcome class — and when a site's letters all agree,
the guard collapses to `1` and the tail to `Xτ` (the `Xa`-family collapse).
Measured site-local factors: ×1.6 (2–4 letters) to ×3.2 (8 letters),
compounding per level through the recursion. Plausible side effect: the
distinct-eventuality count (one `¬β U τ` base case per distinct tail) drops
below Spot's 32-acc-set cap for mid cases, bringing translation-based
verification back.

**Soundness.** Two layers:
- *Globally-equal letters* (same action on every closure config): pure
  alphabet quotient. The construction never needs letters to be minterms —
  only a deterministic action per letter; the class guard is the exact
  characteristic formula of the class, so the input semiautomaton is
  presented isomorphically.
- *Site-local grouping*: within one of the paper's sums, summands for
  σ₁, σ₂ with equal group key are identical formulas up to the guard slot.
  The operator's proved semantics reads "∃ (resp. at no) position k
  satisfying side conditions independent of σ, where σ holds at k".
  Substituting the class guard g = ⋁σᵢ:
  - disjunct position: `∃k: cond ∧ (σ₁∨σ₂)@k ≡ (∃k: cond ∧ σ₁@k) ∨ (∃k: …σ₂…)`
    (same witnessing moment);
  - avoid position: U-left-conjunctivity with shared right side,
    `(¬β₁ U τ) ∧ (¬β₂ U τ) ≡ ¬(β₁∨β₂) U τ` (min-of-witnesses), lifted
    through the recursion; weak forms by duality (`wreach = ¬reach(swapped)`).
  The discipline point is mechanical: each site's group key must contain
  everything the summand reads except the guard — auditable per site, and
  the existing `_dedupe` keys are exactly that plus `li`.

This subsumes the empty-guard half of vacuity pruning (2) and much of the
tail-normalization target (counter-measure D in TODO numbering). Escape
hatch `KR_FUSE_LETTERS=0` restores the per-letter literal paper shape (for
grounding comparisons).

## Key-space diagnosis & structural-reduction experiments (2026-06-13)

A focused session on the reach-driven wall (`Xa & XXa` ≡ `X(a&Xa)`, depth-5,
~24k DAG nodes for a 4-token language). Outcome: the explosion is a **key-space**
problem, and the part of the key that cheap config-graph reasoning can touch is
**not** the driver. Two sound structural reductions tried, both reverted.

**The numbers (probes, now removed; findings here).**
- `a & Xa` with per-node simplify OFF (`KR_SIMP_NODE=0`): 294 DAG nodes → **32
  distinct languages**; **94 ≡ ⊥, 30 ≡ ⊤** (constants written in dozens of
  spellings). But all are `X(0)`-towers — folded by **basics alone**
  (`KR_SIMP_FULL_LIMIT=0` still gives 3 nodes). So `a & Xa` is NOT a wall model;
  basics (scalable, O(1)/node) already nail it.
- `F(a & Xa)`: 111 output nodes ≈ **89 distinct languages** — low redundancy;
  small nodes ⇒ the per-node simplifier canonicalizes and hash-cons merges.
- `Xa & XXa`: basics 30833 → capped-full 23676 → **uncapped-full 16724** (3.9s),
  still ~1600× minimal. Formula-level rewriting (basic OR full, capped OR not)
  **cannot** fold it — Spot's rules are local/pairwise-syntactic; merging
  language-equal-but-syntactically-different BIG nodes needs per-node semantic
  canonicalization = translate-to-automaton = the 32-acc wall.
- Keys vs languages: `Xa & XXa` computes **41,584 helper keys / 19,775 reach
  keys / 10,616 distinct result formulas** for **~tens** of languages
  (Myhill-Nerode bound: 5 residuals + bounded auxiliaries). `|configs| = 7`.
  Shallow cases are efficient (`F(a&Xa)` 167 keys / 59 langs / 4 cfg, ~3×);
  redundancy is **depth-driven**.

**Which axis explodes.** The anatomy (`probe_tail_anatomy`) already showed it:
per level `#τ` grows 4→10→54→422→1507 while `#(S,B,T)` stays ~50–120. The driver
is the **τ-tail**: the solid last-step decomposition rewrites `τ → σ ∧ X τ` each
peel, so τ accumulates the **read suffix**. Two paths reaching the SAME config
carry DIFFERENT accumulated τ but the SAME residual language → keys split,
languages don't. τ re-encodes path history the config already determines.

**Reduction 1 — target-reachability FALSE-cut (suffix-projected, avoid-free).**
Sound (`reach ≡ false` when `T[level:]` graph-unreachable from `S`; the
avoid=B / `T==B` variants are UNSOUND — paper avoid is β-guarded strict-before,
Automata2LTL.txt:573). Payoff: **~zero** (fires 104×/41584 on `Xa & XXa`, census
unchanged; zero on every other case). Reverted.

**Reduction 2 — avoid-vacuity key merge.** `reach(S,B,β,T,τ) ≡
reach(S,None,false,T,τ)` when config `B` is unreachable from `S` (avoid conjunct
vacuous ∀β; clean proof, level-independent). Sound (audit CLEAN, equiv True).
Payoff: **net-NEGATIVE** — `Xa & XXa` −16% (3827 merges) but `G(a->Xb)` +24%,
`G(p->(qUr))` +24%, `Ga|Gb` +23%. Dropping `(B,β)` builds the unconstrained
"free reach" shape, which is often LARGER and shares LESS. Reverted.

**Config-indexed POC (`Acc(c)`, tried then deleted).** `Acc(c) = ` language of D
from config c, memoized per config (key space `|configs|`, not the reach tuple).
Rules: (R1) ⊤/⊥ base by universality/emptiness of the small sub-automaton; (R2)
transient one-step `⋁_σ guard ∧ X Acc(δ(c,σ))`; recurrent ⇒ fall back to BLS. It
WORKED and was equiv-True: `Xa & XXa` 23676→**4**, `Xa & XXXa` 234k→**5**. But
rejected as **off-thesis**: it only handles the safety/transient fragment (the
easy part), uses Spot as a ⊤/⊥ oracle (bypass, not construction), reintroduces a
safety-vs-recurrent case split, and taken to its conclusion abandons the
Krohn-Rhodes cascade entirely — i.e. it is a different (and narrower than
`buchi2ltl/`) construction, not a fix to this one.

**Conclusion (the wall, stated plainly).** The redundancy is the τ-tail =
path-history re-encoding. Collapsing it = recognizing distinct accumulated τ
denote the same residual = **language equality on τ** = exactly the unscalable
Spot operation (32-acc wall). There is no cheap structural proxy: the `(S,B,T)`
axis (reachable by config-graph queries) is provably NOT the driver, and the τ
axis has no graph handle. Within the KR algebra the τ-tail blow-up on
safety/reach-driven inputs appears **irreducible by cheap means**; the two
escapes (a scalable language-equality oracle, or config-indexing) are
respectively the core hard problem itself and off-thesis. **A stronger idea is
needed** — neither structural key surgery nor formula-level rewriting reaches it.

## Acc(c) config-indexing — resurrected, measured, kept (2026-06-13)

The "config-indexing" escape the diagnosis above called off-thesis was rebuilt
and wired (`KR_DISPATCH_ACC`, default ON; `kr/acceptance_dispatch.reconstruct_acc`),
because it is the only thing that reaches the bounded reach wall. This section is
the report on what it is, what it buys, and the experiment that bounds its scope.

**Construction.** `φ := Acc(ι)`, the language of `D` from the initial config, by
bounded unroll of the config graph, memoized per config:

- **R1 (base):** `Acc(c) = ⊤` if `L(D from state_of(c))` is universal, `⊥` if
  empty — a small Spot ⊤/⊥ **oracle on the INPUT automaton D** (lazy + cached,
  `n` states; NOT on the output formula).
- **R2 (unroll):** `Acc(c) = ⋁_σ guard(σ) ∧ X Acc(move_config(c,σ))`.
- **Self-gating:** a non-⊤/⊥ config re-entered on the unroll path is RECURRENT ⇒
  `Acc` declines (`None`) ⇒ caller falls back to the Büchi/coBüchi/Muller chain.
  So it fires only on the bottom/bounded fragment (every path hits ⊤/⊥ within a
  bounded horizon).

It bypasses the reach machinery entirely — no `reach_to`, no `Fin`, no τ-tail —
so it emits the literal formula where BLS pays the blow-up. **It cracks the
standing wall:** `X(a&Xa)` BLS 11835 DAG / 5.1×10⁸ tree / 2069 temporals →
**4 / 5 / 0**, equiv True; the whole X-ladder collapses to literals
(`probe_acc_dispatch`). Complexity is low: `O(|configs| × |Σ|)` memoized builds
plus `≤ n` bounded oracle calls on the tiny `D` — the expensive Spot operation
(translating the large *output*) is exactly what it avoids.

**The objection (it is a syntactic-fragment recogniser) and the experiment.**
Acc was rejected once as "practically pattern matching": it recognises a narrow
class and the cases where it *matters* (deep bounded nesting that makes BLS
explode) may be rare. We quantified this — `probe_acc_fuzz` (kept), 3 seeds of 60
`randltl` formulas (2 APs, tree 8–12), routed through the real
`reconstruct_decomposed` workflow, counting per-piece gate firing:

| seed | tree | gate rate | err/timeout |
|---|---|---|---|
| 1 | 8 | 13/60 = 21.7% | 0/0 |
| 2 | 8 | 17/60 = 28.3% | 0/0 |
| 3 | 12 | 13/60 = 21.7% | 0/0 |

Stable at **~24%**. But the **composition** is the real result: the fired cases
are almost entirely TRIVIAL — pure boolean (`p0`, `!p1`), single/double-X (`Xp1`,
`XX!p0`), or a bounded *piece* of a decomposed mixed formula (`!p1 | Gp0` fires on
the `!p1` arm). These are cases BLS already emits in a handful of nodes; Acc adds
nothing there. The high-value case (deep bounded nesting → BLS blow-up, the
`X(a&Xa)` situation) **did not occur in any seed**. So the ~24% breadth is
illusory: Acc gates a quarter of formulas but its real payoff is confined to a
rare tail that random sampling misses. The `X(a&Xa)` headline is real but
unrepresentative.

**Decision: kept ON despite the narrowness.** The argument for purity (no Spot
oracle in the construction path, no syntactic-fragment recogniser) is real, but
(i) Acc is cheap and self-declining, so the trivial gates are harmless; (ii) the
deep-bounded wall it cracks is exactly the one nothing else in the cascade
machinery reaches; (iii) a measured benchmark case (`X(a&Xa)`) flips
UNVERIFIED→True with zero regressions. The narrowness is recorded honestly here;
the capability is retained. Spin-offs (TODO): replace the Spot ⊤/⊥ oracle with a
structural sink-reachability test on `D` (keep construction Spot-free); per-config
(not whole) BLS fallback at recurrent configs (extend past the pure-bounded class).

## OPEN questions

- **Soundness boundary of pruning (2).** PARTLY SETTLED (2026-06-13, see
  "Key-space diagnosis" above): two config-graph reductions have clean
  correctness arguments — target-reachability FALSE-cut (suffix-projected,
  avoid-free) and avoid-vacuity key merge (B unreachable from S). Both are
  SOUND and both are UNHELPFUL (~zero / net-negative). The remaining vacuity
  arguments would need to bite the τ axis, which has no config-graph handle.
- **Hierarchy preservation under folding.** The paper's outputs land in the
  right MP class by construction (Lemma 5). Do rewrites (3) and interning
  (4) preserve the syntactic class, or do we need class-aware rule sets?
- **How far does interning get?** If most of the b^k tails are
  language-equal modulo delay, interning is near-canonicalization for this
  formula family; if not, the DAG floor stays well above the heuristic's
  answers. Needs measurement, X-ladder first.
- **Is the DAG the right exchange format at all?** Downstream consumers
  (model checkers, Spot) want flat LTL or automata. A DAG-aware translation
  (Spot authors contacted — our outputs are the ideal client) would close
  the loop without ever flattening; until then verification is grounding +
  word sampling, not translation.
- **Does the thesis survive bigger alphabets?** 2^|AP| explicit letters
  multiply b directly (visible already at 3 APs). On-demand letters / BDD
  guards (TODO P2) may be required before any larger benchmark is honest.

## Benchmark protocol (X-ladder)

For each rung `X^k a` (k = 1..): record build time, DAG nodes, distinct
temporal subterms, unfolded tree, and the irreducible reference (heuristic
`sl` output, ~k+2 tokens). Current raw-pipeline rungs: `Xa` 3L (equiv=True),
`XXa` 4L (equiv=True), `XXXa` 5L (4,948 nodes / 1,076 distinct / grounding
clean). Re-measure after each counter-measure lands; the table belongs in
this file.
