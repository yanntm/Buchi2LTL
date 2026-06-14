#!/usr/bin/env python3
"""
kr/simplify/testing/simplify_cli.py

One-formula CLI: show what each stage produces for an argv formula —
the kr/simplify package alone (rules 1+2+3), and the full in-pipeline
node simplification (`kr.ltl_builders._simp_f` = Spot pass + own rules +
bounded Spot closing pass), with an equivalence verdict.

Run from project root:
    python3 kr/simplify/testing/simplify_cli.py "<formula>"
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr.simplify import simplify
from aut2ltl.kr.ltl_builders import _simp_f


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    f = spot.formula(sys.argv[1])
    own = simplify(f)
    pipe = _simp_f(f)
    print(f"input          : {f}")
    print(f"kr/simplify    : {own}")
    print(f"_simp_f (full) : {pipe}")
    print(f"equivalent     : {spot.are_equivalent(f, pipe)}")
    return 0


if __name__ == "__main__":
    main()
