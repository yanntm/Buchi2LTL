# kr/simplify — LTL simplification rules (generic, formula-level)

Standalone LTL simplification over hash-consed `spot.formula` DAGs. This
package is deliberately **independent of the kr/ decomposition**: the rules
apply to any LTL formula. It exists because Spot's `tl_simplifier` — even at
full strength — does none of the rules below (measured: `a & (!a | Fb)` and
`(!a & Xa) | (a & Xa)` survive full simplify untouched; see
`kr/testing/probe_guard_fusion.py` and git history).

Lineage: the rules adapt the boolean-context machinery of the user's Java
engine (`Simplifier.simplifyBoolean`, `LogicSimplifier.evalInInitial` — the
latter an LTL/CTL adaptation of the initial-state strategy of Bonneland et
al., "Simplification of CTL Formulae for Efficient Model Checking of Petri
Nets", PetriNets 2018).

## Rules

| rule | module | status | example |
|---|---|---|---|
| 1. Context pass | `context_pass.py` | DONE | `a & (!a \| G(!a\|Xa))` → `a & G(!a\|Xa)`; `a \| (a&b)` → `a` |
| 2. Now-evaluation | `now_eval.py` | DONE | `a & G(!a)` → `0`; `a & (!a U b)` → `a & b`; `b & (b R c)` → `b & c` |
| 3. Partial factoring | `factor_pass.py` | DONE | `(a&Xb) \| (a&Xc) \| Xd` → `(a&(Xb\|Xc)) \| Xd`; `(a&b) \| (a&!b)` → `a` |
| 4. Unroll-inverse folding | `fold_pass.py` | DONE | `a \| F(!a&Xa)` → `Fa`; `a & G(!a\|Xa)` → `Ga`; `b \| (a & X(aUb))` → `aUb`; S1/S2 subsumption |

### Rule 2 — now-evaluation (`now_rewrite`, hooked into the context pass)

A boolean conjunct `A` in `A ∧ φ` is knowledge about the evaluation
instant of φ — an "initial state" for that subformula, however deeply
nested (LTL adaptation of the initial-state strategy of Bonneland et al.,
PetriNets 2018). Temporal heads under a non-empty context are unrolled
once at that instant; only **shrinking** rewrites apply (see the table in
`now_eval.py`: G/F verdicts, dead-arm reductions `(¬f known) f U g → g`,
`(f known) f R g → g`, and the four constant verdicts). Entailment is
two-tier: hash-consed identity (works for temporal arms) + BDD
implication for propositional nodes. `X` bodies are never touched — the
context legitimately dies at `X`; each body builds its own contexts from
its own skeleton. Trivial constant folds through unary temporal heads
(`X(0)→0` etc.) are done locally; richer folding is Spot-basics
territory downstream.

### Rule 3 — partial factoring (`factor_simplify`)

Greedy shared-term factoring at Or nodes, the SOUND form of the draft
script's idea — only the disjuncts containing the chosen term are grouped,
the rest stay outside: `(t∧A) ∨ (t∧B) ∨ C → (t∧(A∨B)) ∨ C`. Iterated on
the most frequent conjunct (count ≥ 2), each round strictly drops the
disjunct count; the grouped inner Or is factored recursively. Purely
propositional Or nodes (and factored guard groups) go through the
BDD → Minato-ISOP round-trip, accepted only when not larger.

### Rule 4 — unroll-inverse folding (`fold_simplify`)

The kr/ construction emits temporal obligations in locally-unrolled form;
Spot never folds them back. Eight pair-folds (the expansion laws backwards,
valid for arbitrary subformulas): `c | XFc → Fc`, `c & XGc → Gc`,
`g | (f & X(f U g)) → f U g` (same for W; duals for R/M), and the
first-occurrence/induction forms `c | F(¬c & Xc) → Fc`,
`c & G(¬c | Xc) → Gc` (¬c matched two-tier: hash-consed `Not(c)` identity,
then BDD complement). Plus two sibling-subsumption rules (the Formula-5
line redundancy): `c | X(c R d) | G(c | Xd) → c | X(c R d)` and the dual
`c & X(c U d) & F(c & Xd) → c & X(c U d)` — soundness proofs in the module
docstring; the M/W variants are unsound and excluded (regression-tested).
Every rule shrinks the tree AND removes a distinct temporal subformula
(the Couvreur acc-set driver), so folding is the canonical orientation;
now-evaluation only returns constants/arms, so the passes cannot
ping-pong.

Later additions (same module):
- **U/W/R arm-padding removal**: `(c ∧ Xd) U g → c U g` when c ⇒ d and
  g ⇒ d (the Xd conjunct is implied by the U dynamics — every position
  before g fires is followed by c or g), dual for R. Entailment on the
  propositional fragments only (one-way, sound). Found by the census
  class probe: these paddings were the dominant language-equal variant
  pairs in real outputs.
- **G/F absorption**: a conjunct implied by a sibling `Gφ` (the unrolled
  reading `Gφ ≡ φ ∧ XGφ` as an entailment oracle) is dropped; dually a
  disjunct implying a sibling `Fφ`. Entailment is a small syntactic
  recursion (X/F/G bodies, U/M right arms, W/R held arms, And all /
  Or any — each clause a one-line implication), memoized per node pair.
- **Context-aware S1/S2** (`ctx_subsume`, hooked into the context pass as
  `bool_hook`): under a context refuting c, `X(cRd) ∨ G(c∨Xd) → X(cRd)`
  and the one-step-SHIFTED form `X(c ∨ X(cRd)) ∨ G(c ∨ X(c ∨ Xd))` (the
  per-level X-ladder wrapping) — without the context these are NOT
  redundant (witness `!a; a; cycle{!a}`); the initial-state knowledge
  discharges exactly the missing case. Duals at And under ctx ⊨ c.
  This is the rule that pushed `F(a&Xa)` under Spot's 32-acc cap.

The combined entry `kr.simplify.simplify(f)` = context pass (+ now hook)
→ folding → factoring → after a pass that changed something, one more
context pass (and one more fold after factoring — factoring can expose
fold partners). Closing rules like `XF!a | XFa → 1` (F-merge) are
deliberately left to Spot's simplifier downstream of this package.

### Rule 1 — context pass (`context_simplify`)

A single top-down walk of the **boolean skeleton** (And/Or nodes), carrying
two context sets of asserted subformulas:

- at an **And**, every child is rewritten knowing its sibling "atoms"
  (anything that is not And/Or — APs, negated APs, temporal nodes alike)
  are TRUE: positive atoms land in `pos`, `Not(x)` atoms put `x` in `neg`;
- at an **Or**, dually, siblings are rewritten knowing the atom disjuncts
  are FALSE (Shannon: `x ∨ φ ≡ x ∨ φ[x:=false]`);
- any node found in `pos`/`neg` rewrites to `true`/`false` — this is
  **identity-based domination** and works for temporal subformulas too
  (`Gφ & (b | Gφ)` → `Gφ`), since membership is hash-consed identity;
- the context is **reset at every non-boolean operator**: knowledge about
  "now" never crosses X/U/G/F/R/W/M. Bodies are still visited (with an
  empty context), so nested boolean skeletons simplify everywhere;
- temporal siblings are **opened** into now-knowledge (initial-state
  reading): at And, `Gφ` asserts conj(φ) now, `f R g`/`f M g` assert
  conj(g); at Or (Shannon), `Fφ` refutes disj(φ), `f U g`/`f W g` refute
  disj(g) (g@0 alone satisfies U/W). Opened facts flow **ONE-WAY** along
  the canonical child order (earlier → later): two siblings can derive
  the same fact, and bidirectional opening builds circular support —
  in `a & b & (a M b)` the opened b erased the sibling b while the M
  consumed it (fuzz witness `!(b R (Gb & (b M Gb)))` collapsed to 0).
  One-way flow is sound by sequential replacement: child i is rewritten
  in the presence of the ORIGINAL siblings before it. The sibling nodes
  themselves stay bidirectional (support cycles impossible — a node
  cannot be its own subterm);
- constants fold through Spot's constructors (`And([x, ff]) ≡ ff` etc.).

Subsumed classics: unit propagation `a & (!a | φ) → a & φ`, both
absorptions `a & (b|a) → a` and `a | (a&b) → a`, contradiction/tautology
detection `x & !x → false`, `x | !x → true` (via sibling context).

Soundness: rewrites under a context are sound **in place** (the rewritten
child is equivalent only under that context; the enclosing node is
equivalent overall). Hence results must be compared at the ROOT, which is
what the validation harness does.

Memoization is per `(node, pos, neg)`; outside the boolean skeleton the
context is empty, so the bulk of a big DAG memoizes on the node alone —
the pass is O(DAG) there, and context keys stay small (sibling atoms only).

## Usage

```python
import spot
from kr.simplify import context_simplify
f = spot.formula("a & (!a | G(!a | Xa))")
print(context_simplify(f))   # a & G(!a | Xa)
```

Wired into the kr/ construction pipeline since 2026-06-12: `_simp_f` calls
`simplify_node` per DAG node (KR_SIMP_OWN, size cap KR_SIMP_OWN_LIMIT);
KR_SIMP_OWN_FOLD=0 / KR_SIMP_OWN_FACTOR=0 disable rules 4 / 3.

## Testing (`kr/simplify/testing/`)

Same ground rules as `kr/testing/`: placed scripts, run from project root,
timeouts. Every test case validates **language equivalence** of input vs
output via Spot (`spot.are_equivalent` / containment both ways) in addition
to any expected-shape check — a rule that fires is only PASS if the
rewrite is an equivalence.

    python3 kr/simplify/testing/test_context_pass.py
