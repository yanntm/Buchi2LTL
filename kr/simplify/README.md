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
| 2. Now-evaluation | `now_eval.py` | planned | `a & (!a \| (b U !a))` → one-step unroll of U/G/F/R heads under the context |
| 3. Partial factoring | planned | planned | `(g1&Xt) \| (g2&Xt) \| C` → `((g1\|g2)&Xt) \| C` + Minato guard minimize |

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

Not yet wired into the kr/ construction pipeline (`_simp_f`); that
integration is a separate, measured step (TODO 1c).

## Testing (`kr/simplify/testing/`)

Same ground rules as `kr/testing/`: placed scripts, run from project root,
timeouts. Every test case validates **language equivalence** of input vs
output via Spot (`spot.are_equivalent` / containment both ways) in addition
to any expected-shape check — a rule that fires is only PASS if the
rewrite is an equivalence.

    python3 kr/simplify/testing/test_context_pass.py
