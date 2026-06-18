# The LTL simplification algorithm

A generic, **language-preserving** simplifier over hash-consed `spot.formula` DAGs.
It is independent of the construction (`bls`/`decomp`/…): the rules apply to any LTL
formula. It exists because Spot's `tl_simplifier`, even at full strength, does none of
the rewrites below — measured: `a & (!a | Fb)` and `(!a & Xa) | (a & Xa)` survive a
full Spot simplify untouched. Its job is to undo the **locally-unrolled** shapes the
construction emits (`c & XGc`, `1 U Gb`, per-conjunct fairness) that Spot never folds
back, and to exploit **initial-state knowledge** (a boolean sibling is a fact about
*now*) that Spot's purely-structural simplifier ignores.

Lineage: the boolean-context machinery adapts the user's Java engine
(`Simplifier.simplifyBoolean`, `LogicSimplifier.evalInInitial`), the latter an LTL/CTL
take on the initial-state strategy of Bonneland et al. (PetriNets 2018).

## Setting

```
simplify       : formula → formula          -- one combined pipeline pass (idempotent at fixpoint)
simplify_node  : formula → formula          -- memoized fixpoint, per-DAG-node entry
```

Formulas are **hash-consed**: structural equality is pointer identity, so a DAG node is
visited once and results are memoized. `simplify_node` is the pipeline entry the
construction calls per node (`_simp_f`); called bottom-up over a DAG it is amortized
`O(1)` per node — the call count is the **DAG** size, never the unfolded tree.

Two notions recur:

- **Boolean skeleton** — the maximal `And`/`Or` sub-DAG from a node, its leaves being
  *atoms*: anything that is not `And`/`Or` (an AP, a negated AP, or a temporal node).
- **Two-tier entailment** — the oracle behind every conditional rewrite:
  1. **hash-consed identity** — `x ⊨ x` and `Not(x)` recognised by pointer identity;
     works for *temporal* atoms (`Gφ`, `f U g`, …) the BDD layer cannot see;
  2. **BDD implication** — for purely propositional nodes, lifted into buddy and
     tested with `bdd_imp` / cofactored with the Coudert–Madre restrict
     (`prop_cofactor` = `bdd_simplify` over a care-set, then Minato-ISOP back).

## Soundness model

Rewrites fire **under a context** (sibling facts true at the current instant). Such a
rewrite is an equivalence only *in place*: the rewritten child is equivalent to the
original **given the context**, and the enclosing boolean node is equivalent overall.
There is therefore one invariant the whole package obeys and the test harness checks:

> Equivalence is asserted at the **ROOT** (`spot.are_equivalent`, both containments).
> A child rewritten under a non-empty context is *not* equivalent standalone.

Contexts never cross a non-boolean operator: knowledge about "now" is **reset at every
`X`/`U`/`G`/`F`/`R`/`W`/`M`** (bodies are still visited, with an empty context).

## The four passes

Each pass is a bottom-up DAG walk (memoized). They are oriented so they cannot
ping-pong (below).

**1 — Context pass** (`context_pass.py`). A walk of the boolean skeleton carrying two
frozensets `(pos, neg)` of asserted subformulas. At an `And`, every child is rewritten
knowing its sibling *atoms* (any non-`And`/`Or` node — AP, `Not(x)`, or temporal) are
TRUE: positive atoms → `pos`, `Not(x)` → `x ∈ neg`; at an `Or`, dually, knowing the
atom disjuncts are FALSE (Shannon: `x ∨ φ ≡ x ∨ φ[x:=⊥]`). A node found in `pos`/`neg`
collapses to `⊤`/`⊥` (a `Not(x)` with `x` in the dual set likewise) — **identity-based
domination**, valid for temporal atoms too (`Gφ & (b | Gφ) → Gφ`). Beyond the sibling
itself, a temporal sibling is **opened** into now-knowledge (initial-state reading): at
`And`, `Gφ` asserts the conjuncts of `φ@0`, `f R g`/`f M g` assert those of `g@0`; at
`Or`, `Fφ` refutes the disjuncts of `φ@0`, `f U g`/`f W g` those of `g@0`. The sibling
atoms flow bidirectionally (DAG acyclicity rules out support cycles) but the **opened**
facts flow **one-way**, earlier-sibling → later only — bidirectional opening builds
circular support and is unsound (fuzz witness `!(b R (Gb & (b M Gb)))` collapsed to
`0`). Because one-way flow makes the result depend on traversal order (sound for any
fixed order, but more or less *complete*), children are visited **now-fact producers
first** (`_open_rank`, polarity-aware: `G`/`R`/`M` at `And`, `F`/`U`/`W` at `Or`, strong
before weak; consumers last), so each opening reaches the most siblings — free, since
Spot re-canonicalises the rebuilt node and the operand list is tiny. When the And/Or
constructor exposes a new atom sibling (fold/flatten), the node is re-walked. Subsumes the classics: unit propagation, both absorptions,
contradiction/tautology.

**2 — Now-evaluation** (`now_eval.py`, hooked into the context pass as `now_hook`). A
boolean conjunct `A` in `A ∧ φ` is an *initial state* for `φ`, however deeply nested.
A temporal head under a non-empty context is unrolled once at that instant via its
expansion law, and **only shrinking rewrites are kept**:

```
G f    : ctx ⊨ ¬f        → ⊥                 (G f ≡ f ∧ XG f)
F f    : ctx ⊨ f         → ⊤                 (F f ≡ f ∨ XF f)
f U/W g: ctx ⊨ g         → ⊤   ;  ctx ⊨ ¬f∧¬g → ⊥   ;  ctx ⊨ ¬f → g
f R/M g: ctx ⊨ ¬g        → ⊥   ;  ctx ⊨ f∧g   → ⊤   ;  ctx ⊨ f  → g
```

— so the outcome is always a constant or an existing arm `g`, never an unrolled form.
`X` bodies are never touched: knowledge is about NOW and legitimately dies at `X`. The
returned arm is at the same instant, so the context pass keeps simplifying it under the
same context. (Entailment `ctx ⊨ x` is the two-tier oracle; the trivial post-rewrite
constant folds `X⊥→⊥`, `G⊤→⊤`, … are done by `context_pass._const_fold`, not here.)

**3 — Partial factoring** (`factor_pass.py`). The sound form of shared-term factoring
at `Or`: only the disjuncts containing the chosen term are grouped, the rest stay out —
`(t∧A) ∨ (t∧B) ∨ C → (t∧(A∨B)) ∨ C`, iterated on the most frequent conjunct
(count ≥ 2), each round strictly dropping the disjunct count. Purely propositional `Or`
nodes go through the BDD → Minato-ISOP round-trip, accepted only when not larger.
Factoring can *raise* the distinct-temporal count (variant forms coexist across
branches), so it is the one census-non-monotone pass and is gated (`KR_SIMP_OWN_FACTOR`).

**4 — Unroll-inverse folding** (`fold_pass.py`). The construction emits temporal
obligations in locally-unrolled form; this pass runs the expansion laws **backwards**.
It has two application sites in the walk.

*At a boolean node*, `_fold_node` loops to a fixpoint, each step **dropping a child**
via — in this order — absorption, then sibling-subsumption, then a fold; `_gffg_cofactor`
then runs on the result:
- *folds* (each a plain equivalence for arbitrary subformulas): pair-folds
  `c | XFc → Fc`, `c & XGc → Gc`; the first-occurrence/induction forms
  `c | F(¬c & Xc) → Fc`, `c & G(¬c | Xc) → Gc`; the binary expansions
  `g | (f & X(f U g)) → f U g` (and `W`; duals `R`/`M`); and the full `W`/`M`/`R`/`U`
  expansion **quartet** carrying the construction's strengthened modal body (e.g.
  `G(f ∧ ¬g) ∨ (f U g) → f W g`), sound because the strengthening collapses back to the
  plain law — the body must be the bare arm or that arm plus a single negated-other-arm
  term, anything more is unsound (regression-tested);
- *G/F absorption*: a conjunct implied by a sibling `Gφ` is dropped (reading
  `Gφ ≡ φ ∧ XGφ`), dually a disjunct implying a sibling `Fφ`; entailment is a small
  sound-but-incomplete syntactic recursion (`_g_implies`/`_implies_f`, memoized);
- *unconditional sibling-subsumption* (the Formula-5 redundancy):
  `c ∨ X(c R d) ∨ G(c ∨ Xd) → c ∨ X(c R d)` when the bare `c` and `X(c R d)` siblings
  are both present (dual S2 at `And`); `W`/`M` variants unsound, excluded;
- *GF/FG sibling cofactoring* (`_gffg_cofactor`): under a cofinite invariant `FG ψ` a
  tail-only `GF φ` matters only where `ψ` holds, so `GF φ ∧ FG ψ → GF(φ|_ψ) ∧ FG ψ`
  (e.g. `GF(a&b) ∧ FG b → GF a ∧ FG b`), `φ|_ψ` the `prop_cofactor` restrict, kept only
  when strictly smaller; literal dual at `Or`. The invariant **source** is the literal
  `FG ψ`/`GF β` OR any **strong** until/release that entails it — `φ U G(ψ) ⟹ FG ψ`,
  dual `φ R F(β)` (false-case `¬φ U G(¬β) ⟹ FG ¬β`); weak `W`/`M` give none.

*At a temporal node*, two care-set restrictions of an arm (`prop_cofactor`, no temporal
node added/removed): `_arm_unpad` drops padding — `(c ∧ Xd) U g → c U g` when `c ⇒ d`
and `g ⇒ d` (dual `R`); `_arm_cofactor` restricts a fully-propositional left arm —
`φ U ψ → φ' U ψ` agreeing on `{ψ false}` (dual `R`/`M` on `{ψ true}`).

The **context-aware** S1/S2 (`ctx_subsume`) lives in this module but is applied during
the *context pass* (its `bool_hook`): the initial-state knowledge discharges the missing
`c`, so `X(c R d) ∨ G(c ∨ Xd) → X(c R d)` even with no bare-`c` sibling — the rule that
pushed `F(a&Xa)` under Spot's 32-acceptance-set cap.

Every fold **shrinks the tree AND removes a distinct temporal subformula** — the
Couvreur acceptance-set driver — so folding is the canonical orientation, and (since
now-evaluation only ever emits a constant or an existing arm) the two cannot ping-pong.

## Pipeline and termination

```
simplify(f) =
    g  = context(f)                       -- pass 1 (+ now hook 2, + ctx_subsume on bool nodes)
    g  = context(fold(g))   if changed    -- pass 4, re-contextualise on change
    h  = factor(g)                        -- pass 3
    if h changed: h = context(h); h = context(fold(h)) if changed
    return h
```

Termination rests on **orientation**, not a global measure: folding only ever returns
a strictly smaller tree with one fewer eventuality; now-evaluation only ever returns a
**constant or an existing arm** — never an unrolled form. So the two cannot ping-pong
(fold → unrolled-shape, now → constant/arm are disjoint codomains). Factoring strictly
drops the `Or` arity each round. The per-pass walks are memoized fixpoints, so each
reaches a fixpoint in finitely many node visits.

## Cost

Memoization is keyed `(node, pos, neg)`. Outside the boolean skeleton the context is
empty, so the bulk of a large DAG memoizes on the node alone — `O(DAG)` there, with
context keys staying small (sibling atoms only). The BDD round-trips are bounded by the
propositional fan-in of a single node, not the formula. Net: the simplifier is linear
in the DAG it is handed, which is why `simplify_node` is safe to call per node across
the whole construction output.
