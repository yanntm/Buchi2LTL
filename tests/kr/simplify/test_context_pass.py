#!/usr/bin/env python3
"""
kr/simplify/testing/test_context_pass.py

Validation for Rule 1 (context pass). Every case checks:
  1. language equivalence input == output (Spot, both containments) —
     a rewrite is only PASS if it is an equivalence;
  2. when an expected output is given, structural equality to it
     (hash-consed comparison after parsing the expected string);
  3. cases marked must_not_change assert the pass left the formula alone
     (boundary safety: no context leaking under temporal operators).

Run from project root:
    python3 kr/simplify/testing/test_context_pass.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr.simplify import context_simplify

# (input, expected_output or None, note) — expected None = only equivalence
# + change/no-change is checked.
CASES = [
    # unit propagation through a disjunction (the Ga pipeline shape)
    ("a & (!a | G(!a | Xa))", "a & G(!a | Xa)", "unit prop into Or"),
    ("a & (!a | Fb)", "a & Fb", "unit prop, temporal sibling"),
    # absorptions, both directions
    ("a & (b | a)", "a", "And-side absorption"),
    ("!a & (b | a)", "!a & b", "neg literal drops disjunct"),
    ("a | (a & b)", "a", "Or-side absorption (Shannon)"),
    ("!a | (a & b)", "!a | b", "Or-side Shannon with negation"),
    # contradiction / tautology via sibling context
    ("a & b & (!a | !b)", "0", "conjunction refutes the clause"),
    ("a | !a", "1", "tautology (spot constructor or context)"),
    # temporal-sibling opening (initial-state reading, ONE-WAY flow);
    # circularity soundness regressions: with bidirectional opening these
    # collapsed to a / 0 (the fuzz witness) — they must keep all conjuncts
    # (full M reduction needs the now-hook: see test_now_eval; opening flow
    # is one-way along spot's canonical child order, so only shapes where
    # the temporal sibling sorts first can fire here)
    ("a & b & (a M b)", None, "M circularity regression (no collapse to a)"),
    ("!(b R (Gb & (b M Gb)))", None, "fuzz witness: no mutual-support collapse"),
    ("Ga & (!a | Xb)", "Ga & Xb", "G body opened: a kills the !a disjunct"),
    # identity domination on TEMPORAL subformulas
    ("Ga & (b | Ga)", "Ga", "temporal absorption"),
    ("(a U b) | ((a U b) & c)", "a U b", "temporal Or-absorption"),
    # deep nesting: the user's real pipeline example (== a & Xa & stuff)
    ("a & (!a | (a & ((((a & X(F(!a))) | (!a & X(F(!a)))) & (!a | Xa)) | "
     "((!a | Xa) & ((!a & X(F(a))) | (a & X(F(a))))))))",
     "a & ((X(F!a) & Xa) | (Xa & X(Fa)))",
     "user example (20-node real output)"),
    # context applies INSIDE temporal bodies, from their own skeleton
    ("X(a & (!a | b))", "X(a & b)", "fresh context inside X body"),
    ("G(c & (!c | d))", "G(c & d)", "fresh context inside G body"),
    # boundary safety: context must NOT cross temporal operators
    ("a | X(a & b)", None, "no leak under X (must not change)"),
    ("a & F(!a & b)", None, "no leak under F (must not change)"),
    ("a & X(!a)", None, "no leak under X (must not change)"),
]

MUST_NOT_CHANGE = {"a | X(a & b)", "a & F(!a & b)", "a & X(!a)"}


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
        out = context_simplify(f)
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
