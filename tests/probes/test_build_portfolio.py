#!/usr/bin/env python3
"""
Smoke test for aut2ltl.portfolio.build.build_portfolio.

Covers the assembly logic only (cheap — building a Translator triggers NO GAP
decomposition; that happens when it is CALLED). One GAP-free functional check
runs the `muller` leaf on a very-weak formula. Self-bound, no Spot/GAP waits.

    python3 tests/test_build_portfolio.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aut2ltl.options import Options
from aut2ltl.bls.options import KR_OPTIONS
from aut2ltl.portfolio.build import build_portfolio, TECHNIQUES
from aut2ltl.language import Language

_opts = Options.from_specs(KR_OPTIONS)
_fail = []


def check(cond: bool, msg: str) -> None:
    print(("ok  " if cond else "FAIL") + " : " + msg)
    if not cond:
        _fail.append(msg)


# --- default assembly (techniques=None) resolves to the `default` alias, whatever
# recipe that currently points at (the single source of truth is RECIPES["default"];
# no test should name the shipped recipe and need editing on each adoption) ---
top = build_portfolio(_opts)
named_default = build_portfolio(_opts, {"default"})
check(getattr(top, "name", None) == getattr(named_default, "name", None),
      "techniques=None resolves to the 'default' recipe")
check(callable(top), "default is callable")
# --- the recipe cited by name resolves to the same shape ---
best = build_portfolio(_opts, {"best"})
check(getattr(best, "name", None) == "simplify", "--use best top is a Simplify")

# --- cited single producer (the general muller leaf) ---
muller = build_portfolio(_opts, {"muller"})
check(callable(muller), "build {'muller'} is callable")

# --- cited ladder: one grouped kr rung (buchi) + the bls cascade rung ---
ladder = build_portfolio(_opts, ["buchi", "bls"])
check(getattr(ladder, "name", None) == "cited", "buchi,bls is a 'cited' ladder")
check(len(ladder._stages) == 2, "buchi rung + bls cascade rung => 2 rungs total")

# --- kr leaves collapse into a single grouped rung ---
collapsed = build_portfolio(_opts, ["acc", "buchi", "muller"])
check(getattr(collapsed, "name", None) != "cited",
      "three kr leaves collapse to one rung (returned directly, not a 'cited' ladder)")

# --- bls is the integrated cascade as a producer ---
bare_bls = build_portfolio(_opts, ["bls"])
check(callable(bare_bls), "build {'bls'} is callable")

# --- validation ---
for bad, why in [({"nope"}, "unknown technique"), ([], "producer-free citation")]:
    try:
        build_portfolio(_opts, bad)
        check(False, f"{why} raises ValueError")
    except ValueError:
        check(True, f"{why} raises ValueError")

check(set(TECHNIQUES) == {"acc", "weak", "buchi", "cobuchi", "muller", "bls"},
      "TECHNIQUES vocabulary is the 6 producer names")

# --- one GAP-free functional run: the muller leaf on a very-weak formula ---
muller_only = build_portfolio(_opts, ["muller"])
res = muller_only(Language.of_ltl("F a"))
check(res.ok and res.formula is not None, "muller translates 'F a' (no GAP)")

print()
if _fail:
    print(f"FAILED {len(_fail)} check(s)")
    sys.exit(1)
print("ALL OK")
