#!/usr/bin/env python3
"""
Smoke test for aut2ltl.best_of + LTLResult.cost (GAP-free; bare spot.formula
DAGs in, no engine, stages are plain lambdas ignoring their input).

    python3 tests/test_best_of.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import spot

from aut2ltl.result import LTLResult
from aut2ltl.best_of import best_of
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

# --- LTLResult.cost -----------------------------------------------------------
check(LTLResult.success(SMALL, "x").cost == dag_node_count(SMALL) == 1,
      "cost of an OK result = dag_node_count of its formula")
check(LTLResult.decline().cost is None, "a DECLINED result has no cost (None)")
check(LTLResult.not_definable().cost is None, "a NOT_LTL result has no cost (None)")

acc = LTLResult.start("seed")
check(acc.cost is None, "an accumulator with no formula yet has no cost")
acc.formula = BIG
check(acc.cost == 3, "cost computes once the formula is filled")
acc.formula = SMALL
check(acc.cost == 1, "cost cache invalidates when the formula is reset")

# --- best_of: minimal-cost selection -----------------------------------------
r = best_of([const(LTLResult.success(BIG, "big")),
             const(LTLResult.success(SMALL, "small")),
             const(LTLResult.success(MID, "mid"))], name="t")(None)
check(r.ok and r.formula == SMALL, "best_of returns the least-cost OK stage")
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

# --- custom key ---------------------------------------------------------------
# Pick the LARGEST instead, by negating the cost.
r = best_of([const(LTLResult.success(SMALL, "small")),
             const(LTLResult.success(BIG, "big"))],
            name="t", key=lambda res: -(res.cost or 0))(None)
check(r.formula == BIG, "a custom key selects on its own measure (here: largest)")

print()
if _fail:
    print(f"FAILED {len(_fail)} check(s)")
    sys.exit(1)
print("ALL OK")
