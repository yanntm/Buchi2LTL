#!/usr/bin/env python3
"""
Smoke test for aut2ltl.portfolio.build.build_portfolio.

Covers the assembly logic only (cheap — building a Translator triggers NO GAP
decomposition; that happens when it is CALLED). One GAP-free functional check
runs the `sl`-only ladder on a very-weak formula. Self-bound, no Spot/GAP waits.

    python3 tests/test_build_portfolio.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aut2ltl.options import Options
from aut2ltl.portfolio import PORTFOLIO_OPTIONS
from aut2ltl.kr.options import KR_OPTIONS
from aut2ltl.portfolio.build import build_portfolio, TECHNIQUES
from aut2ltl.language import Language

_opts = Options.from_specs(PORTFOLIO_OPTIONS + KR_OPTIONS)
_fail = []


def check(cond: bool, msg: str) -> None:
    print(("ok  " if cond else "FAIL") + " : " + msg)
    if not cond:
        _fail.append(msg)


# --- default assembly (techniques=None) ---
top = build_portfolio(_opts)
check(getattr(top, "name", None) == "decompose", "default top is a Decompose")
check(callable(top), "default is callable")

# --- cited single producer (pure BLS) ---
bls = build_portfolio(_opts, {"bls"})
check(callable(bls), "build {'bls'} is callable")
check(getattr(bls, "name", None) != "decompose", "pure bls is not wrapped")

# --- cited ladder, order + kr-grouping ---
ladder = build_portfolio(_opts, ["sl", "buchi", "bls"])
# sl rung + one grouped kr rung (buchi,bls collapse) => 2 rungs, name 'cited'
check(getattr(ladder, "name", None) == "cited", "sl,buchi,bls is a 'cited' ladder")
check(len(ladder._stages) == 2, "buchi+bls collapse to one kr rung (2 rungs total)")

# --- wrappers ---
wrapped = build_portfolio(_opts, ["decompose", "acc", "bls"])
check(getattr(wrapped, "name", None) == "decompose", "decompose,acc,bls -> Decompose outer")
driven = build_portfolio(_opts, ["sl_driven", "buchi"])
check(getattr(driven, "name", None) == "sl_driven", "sl_driven,buchi -> SlDriven outer")

# --- validation ---
for bad, why in [({"nope"}, "unknown technique"), ({"decompose"}, "producer-free citation")]:
    try:
        build_portfolio(_opts, bad)
        check(False, f"{why} raises ValueError")
    except ValueError:
        check(True, f"{why} raises ValueError")

check(set(TECHNIQUES) == {"acc", "weak", "buchi", "cobuchi", "bls", "sl",
                          "sl_driven", "decompose"}, "TECHNIQUES vocabulary is the 8 names")

# --- one GAP-free functional run: sl gate on a very-weak formula ---
sl_only = build_portfolio(_opts, ["sl"])
res = sl_only(Language.of_ltl("F a"))
check(res.ok and res.formula is not None, "sl-only translates 'F a' (no GAP)")

print()
if _fail:
    print(f"FAILED {len(_fail)} check(s)")
    sys.exit(1)
print("ALL OK")
