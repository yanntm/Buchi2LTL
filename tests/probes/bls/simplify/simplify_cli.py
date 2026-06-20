#!/usr/bin/env python3
"""
bls/simplify/testing/simplify_cli.py

One-formula CLI: show what each stage produces for an argv formula —
the bls/simplify package alone (rules 1+2+3), and the full in-pipeline
node simplification (`kr.ltl_builders._simp_f` = Spot pass + own rules +
bounded Spot closing pass), with an equivalence verdict.

Run from project root:
    python3 bls/simplify/testing/simplify_cli.py "<formula>"
"""

import sys

import spot

from aut2ltl.ltl.simplify import simplify
from aut2ltl.ltl.builders import _simp_f

def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    f = spot.formula(sys.argv[1])
    own = simplify(f)
    pipe = _simp_f(f)
    print(f"input          : {f}")
    print(f"bls/simplify    : {own}")
    print(f"_simp_f (full) : {pipe}")
    print(f"equivalent     : {spot.are_equivalent(f, pipe)}")
    return 0

if __name__ == "__main__":
    main()
