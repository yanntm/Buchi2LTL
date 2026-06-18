#!/usr/bin/env python3
"""
Smoke test for aut2ltl.best_of (GAP-free; bare spot.formula DAGs in, no engine,
stages are plain lambdas ignoring their input). Size is derived by the comparators
from the result formula — there is no score field on LTLResult.

    python3 tests/test_best_of.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import spot

from aut2ltl.result import LTLResult
from aut2ltl.best_of import best_of, significantly_smaller
from aut2ltl.ltl.metrics import dag_node_count

_fail = []


def check(cond: bool, msg: str) -> None:
    print(("ok  " if cond else "FAIL") + " : " + msg)
    if not cond:
        _fail.append(msg)


# A stage is Language -> LTLResult; here the input is ignored.
def const(r: LTLResult):
    return lambda _lang: r


SMALL = spot.formula("a")            # dag 1
BIG = spot.formula("a & b")          # dag 3 (And, a, b)
MID = spot.formula("G a")            # dag 2 (G, a)

check(dag_node_count(SMALL) == 1 and dag_node_count(BIG) == 3 and dag_node_count(MID) == 2,
      "fixture sizes are 1 / 3 / 2 DAG nodes")

# --- best_of: minimal-size selection (default `smaller`) ----------------------
r = best_of([const(LTLResult.success(BIG, "big")),
             const(LTLResult.success(SMALL, "small")),
             const(LTLResult.success(MID, "mid"))], name="t")(None)
check(r.ok and r.formula == SMALL, "best_of returns the least-size OK stage")
check(r.technique == frozenset({"small"}),
      "the winner is returned UNCHANGED (its technique, no tag of best_of's own)")

# --- tie-break keeps the earlier stage ---------------------------------------
a1 = spot.formula("X a")             # dag 2
a2 = spot.formula("X b")             # dag 2 (same cost)
r = best_of([const(LTLResult.success(a1, "first")),
             const(LTLResult.success(a2, "second"))], name="t")(None)
check(r.technique == frozenset({"first"}), "ties keep the earlier stage")

# --- DECLINED falls through, all-decline -> decline --------------------------
r = best_of([const(LTLResult.decline("nope")),
             const(LTLResult.success(BIG, "big"))], name="t")(None)
check(r.ok and r.formula == BIG, "a DECLINED stage falls through to an OK one")
r = best_of([const(LTLResult.decline()), const(LTLResult.decline())], name="t")(None)
check(r.declined, "every stage declined -> a bare decline")

# --- NOT_LTL short-circuits (absorbing) --------------------------------------
def boom(_lang):
    raise AssertionError("stage after a NOT_LTL must not run")

r = best_of([const(LTLResult.success(BIG, "big")),
             const(LTLResult.not_definable("not ltl", "verdict")),
             boom], name="t")(None)
check(r.not_ltl, "a NOT_LTL verdict short-circuits best_of")

# --- custom comparator (the pluggable seam) ----------------------------------
# Prefer the LARGEST: challenger beats incumbent iff its formula has more nodes.
r = best_of([const(LTLResult.success(SMALL, "small")),
             const(LTLResult.success(BIG, "big"))],
            name="t",
            beats=lambda inc, ch: dag_node_count(ch.formula) > dag_node_count(inc.formula))(None)
check(r.formula == BIG, "a custom `beats` selects on its own policy (here: largest)")

# --- significance margin: a tiny win does NOT unseat the trusted incumbent ----
small_win = spot.formula("a & b & c")    # dag 4, one less than...
incumb = spot.formula("a & b & c & d")   # dag 5
r = best_of([const(LTLResult.success(incumb, "first")),
             const(LTLResult.success(small_win, "challenger"))],
            name="t", beats=significantly_smaller(rel=0.5, floor=3))(None)
check(r.technique == frozenset({"first"}),
      "a 1-node win below the margin keeps the trusted first answer")

# --- significance margin: a big win DOES unseat it ---------------------------
big_win = spot.formula("a")              # dag 1, four less than incumb (>= floor 3)
r = best_of([const(LTLResult.success(incumb, "first")),
             const(LTLResult.success(big_win, "challenger"))],
            name="t", beats=significantly_smaller(rel=0.5, floor=3))(None)
check(r.technique == frozenset({"challenger"}),
      "a win past the margin (4 >= max(3, ceil(.5*5))) takes over")

print()
if _fail:
    print(f"FAILED {len(_fail)} check(s)")
    sys.exit(1)
print("ALL OK")
