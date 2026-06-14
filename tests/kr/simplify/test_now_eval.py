#!/usr/bin/env python3
"""
kr/simplify/testing/test_now_eval.py

Validation for Rule 2 (now-evaluation) via the combined `simplify`
pipeline (context pass + now hook). Same harness contract as
test_context_pass: every case is PASS only if the rewrite is a
Spot-verified language equivalence; expected shapes checked when given;
MUST-NOT-CHANGE cases assert boundary safety.

Run from project root:
    python3 kr/simplify/testing/test_now_eval.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr.simplify import simplify

CASES = [
    # G / F heads under a literal context
    ("a & G(!a)", "0", "G refuted at its first instant"),
    ("a & F(a)", "a", "F satisfied now"),
    ("a & (b | G(!a))", "a & b", "G refuted inside a disjunction"),
    # U / W: dead left arm -> right arm at the same instant
    ("a & (!a U b)", "a & b", "U left arm dead -> right arm"),
    ("a & (!a W b)", "a & b", "W left arm dead -> right arm"),
    ("a & (!a U !a)", "0", "U both arms dead"),
    ("a & (b U a)", "a", "U right arm true now"),
    # R / M
    ("b & (b R c)", "b & c", "R left arm true -> right arm"),
    ("a & (c R !a)", "0", "R right arm refuted now"),
    ("a & b & (a M b)", "a & b", "M satisfied now"),
    # BDD-backed propositional entailment (beyond identity)
    ("(a & b) & G(!a | !b)", "0", "G body refuted via BDD"),
    ("a & b & F(a | c)", "a & b", "F body entailed via BDD"),
    # nested instants: each X-body gets its own context
    ("a & X(b & F(b))", "a & Xb", "inner F at the inner instant"),
    ("X(a & G(!a))", "0", "refutation inside an X body (X(0) folds)"),
    # the Ga pipeline shape: context kills the vacuous disjunct, then the
    # rule-4 induction fold closes it (was `a & G(!a | Xa)` pre-fold)
    ("a & (!a | G(!a | Xa))", "Ga", "context + induction fold close to Ga"),
    # boundary safety
    ("a & X(F(!a))", None, "no leak under X (must not change)"),
    ("a & (b U X!a)", None, "X arm opaque (must not change)"),
    ("a & G(b | !a)", None, "G body satisfiable under ctx (must not change)"),
]

MUST_NOT_CHANGE = {"a & X(F(!a))", "a & (b U X!a)", "a & G(b | !a)"}


def equiv(f: "spot.formula", g: "spot.formula") -> bool:
    try:
        return spot.are_equivalent(f, g)
    except AttributeError:
        a, b = f.translate(), g.translate()
        return spot.contains(a, b) and spot.contains(b, a)


def main() -> int:
    failures = 0
    for src, expected, note in CASES:
        f = spot.formula(src)
        out = simplify(f)
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
