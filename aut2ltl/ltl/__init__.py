"""
aut2ltl.ltl — the shared LTL / Spot / BDD machinery (a contract-floor package).

Generic, engine-agnostic utilities for manipulating LTL as `spot.formula` DAGs,
plus the buddy-BDD plumbing both engines lean on. It sits BELOW every engine
(`kr`, `sl`) and the portfolio, so they all import LTL helpers from here rather
than reaching into one engine for them. It is heavily Spot/buddy dependent by
nature; that dependency is concentrated here.

Members:
- `builders`     — guard strings, native `spot.formula` builders (`_And`/`_Or`/`_X`/
                   `_U`/...), the simplify entry (`_simp_f` / `simplify_ltl` /
                   `normalize_ltl`), stringify (`_str_f`/`_short_f`), `_tree_size_f`.
- `simplify/`    — the "own simplify" rewrite passes (context / now-eval / factor /
                   fold) that Spot lacks; `builders._simp_f` runs them per node.
- `bdd_utils`    — reliable buddy-BDD construction from a Spot automaton (AP→var
                   map + point/cube BDDs); used by `kr.extract` for letter
                   classification during decomposition.

Import the members directly (`from aut2ltl.ltl.builders import _simp_f`); this
package init intentionally stays thin to avoid import-order surprises.
"""
