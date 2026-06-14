#!/usr/bin/env python3
"""
kr/simplify/testing/test_factor_pass.py

Validation for Rule 3 (partial factoring) — factor_simplify alone for the
core cases, the combined `simplify` pipeline for the end-to-end ones.
Harness contract as the other suites: PASS requires Spot-verified language
equivalence; expected shapes when given; the soundness-bug regression case
from the draft script is here for good.

Run from project root:
    python3 kr/simplify/testing/test_factor_pass.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr.simplify import factor_simplify, simplify

# (input, expected or None, use_pipeline, note)
CASES = [
    # plain shared-tail factoring
    ("(a & Xc) | (b & Xc)", "(a | b) & Xc", False, "two guards, one tail"),
    ("(a & Xc & Gd) | (b & Gd & Xc)", "(a | b) & Xc & Gd", False,
     "multi-conjunct tail, order-insensitive"),
    # THE regression: draft script wrapped the outsider — must stay outside
    ("(a & Xb) | (a & Xc) | Xd", "(a & (Xb | Xc)) | Xd", False,
     "outsider stays outside (draft-bug regression)"),
    # Minato minimization of the factored guard group
    ("(!a & !b & Xc) | (!a & b & Xc) | (a & b & Xc)", "(!a | b) & Xc", False,
     "3 minterms -> Minato !a|b"),
    ("(a & Xc) | (!a & Xc)", "Xc", False, "guards fuse to true"),
    # purely propositional Or minimized directly
    ("(a & b) | (a & !b)", "a", False, "propositional Or -> Minato"),
    # temporal shared term (the user-script example, via pipeline)
    ("a & ((XF!a & Xa) | (Xa & XFa))", "a & Xa & (XF!a | XFa)", True,
     "factor Xa out (user example)"),
    # full chain: context+now+factor on the deep real-output example
    ("a & (!a | (a & ((((a & X(F(!a))) | (!a & X(F(!a)))) & (!a | Xa)) | "
     "((!a | Xa) & ((!a & X(F(a))) | (a & X(F(a))))))))",
     "a & Xa & (XF!a | XFa)", True, "deep example through full pipeline"),
    # nothing in common: untouched
    ("(a & Xc) | (b & Xd)", None, False, "no shared term (must not change)"),
    ("Xa | Xb", None, False, "bare disjuncts (must not change)"),
]

MUST_NOT_CHANGE = {"(a & Xc) | (b & Xd)", "Xa | Xb"}


def equiv(f: "spot.formula", g: "spot.formula") -> bool:
    try:
        return spot.are_equivalent(f, g)
    except AttributeError:
        a, b = f.translate(), g.translate()
        return spot.contains(a, b) and spot.contains(b, a)


def main() -> int:
    failures = 0
    for src, expected, use_pipeline, note in CASES:
        f = spot.formula(src)
        out = simplify(f) if use_pipeline else factor_simplify(f)
        ok_equiv = equiv(f, out)
        ok_shape = True
        detail = ""
        if expected is not None:
            ok_shape = (out == spot.formula(expected))
            if not ok_shape:
                detail = f" expected={expected!r}"
        if src in MUST_NOT_CHANGE and out != f:
            ok_shape = False
            detail = " MUST-NOT-CHANGE but changed"
        status = "PASS" if (ok_equiv and ok_shape) else "FAIL"
        if status == "FAIL":
            failures += 1
        print(f"  {status}  [{note}] {src}")
        print(f"        -> {out}"
              f"{'' if ok_equiv else '  ** NOT EQUIVALENT **'}{detail}")
    print(f"\n{'CLEAN' if failures == 0 else f'{failures} FAILURE(S)'} "
          f"({len(CASES)} cases)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
