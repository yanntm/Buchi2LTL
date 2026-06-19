# aut2ltl/ltl/simplify — LTL simplification (source map)

Standalone, **language-preserving** LTL simplification over hash-consed
`spot.formula` DAGs, independent of the construction. It does rewrites Spot's
`tl_simplifier` does not — undoing the locally-unrolled shapes the construction emits
(`c & XGc`, `1 U Gb`, per-conjunct fairness) and exploiting **initial-state knowledge**
(a boolean sibling is a fact about *now*).

> **The construction and soundness spec is [`algorithm.md`](algorithm.md)** — the four
> passes, the root-equivalence soundness model, the rule catalogue with soundness hooks,
> the pipeline, termination, and cost. Read it for the *why*; this file is the map.

Lineage: the boolean-context machinery adapts the user's Java engine
(`Simplifier.simplifyBoolean`, `LogicSimplifier.evalInInitial`), the latter an LTL/CTL
take on the initial-state strategy of Bonneland et al. (PetriNets 2018).

## Module map

```
formula ──context(+now hook +ctx_subsume)──▶ fold ──▶ factor ──▶ (re-passes) ──▶ formula
```

- **`context_pass.py`** — Rule 1: a context-carrying walk of the boolean skeleton
  (`pos`/`neg` asserted-subformula sets, identity domination, one-way now-fact opening
  with producer-first traversal). Hosts the rule-2 and `ctx_subsume` hooks.
- **`now_eval.py`** — Rule 2: one-step temporal unrolling under context (shrinking
  verdicts only). Also home to the BDD helpers the other passes share: `prop_minimize`
  (Minato-ISOP), `prop_cofactor` (Coudert–Madre restrict), the two-tier entailment.
- **`factor_pass.py`** — Rule 3: sound partial factoring at `Or` (+ propositional
  BDD→ISOP), gated by `KR_SIMP_OWN_FACTOR` (the one census-non-monotone pass).
- **`fold_pass.py`** — Rule 4: unroll-inverse folding (the expansion laws backwards,
  the `W`/`M`/`R`/`U` quartet, G/F absorption, sibling-subsumption, `_gffg_cofactor`,
  the arm rules) + `ctx_subsume`. Gated by `KR_SIMP_OWN_FOLD`.
- **`__init__.py`** — the combined `simplify(f)` pipeline and the memoized per-node
  fixpoint `simplify_node(f)` the construction calls (`_simp_f`).

## Usage

```python
import spot
from aut2ltl.ltl.simplify import simplify, simplify_node, context_simplify
simplify(spot.formula("a & (!a | G(!a | Xa))"))   # a & G(!a | Xa)
```

Wired into the construction pipeline since 2026-06-12: `_simp_f` calls `simplify_node`
per DAG node (`KR_SIMP_OWN`, size cap `KR_SIMP_OWN_LIMIT`); `KR_SIMP_OWN_FOLD=0` /
`KR_SIMP_OWN_FACTOR=0` disable rules 4 / 3.

## Testing (`tests/bls/simplify/`)

Placed scripts, run from project root, under timeout. Every firing validates **language
equivalence** of input vs output via Spot (`spot.are_equivalent` / both containments) on
top of any expected-shape check — a rule that fires is PASS only if the rewrite is an
equivalence. `test_random_equiv.py` fuzzes it (`[N] [seed] [n_aps] [tree_size]`).

```
python3 tests/bls/simplify/test_context_pass.py
python3 tests/bls/simplify/test_random_equiv.py
```
