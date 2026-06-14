#!/usr/bin/env python3
"""
kr/simplify/testing/test_fold_pass.py

Validation for Rule 4 (unroll-inverse folding) — fold_simplify alone for
the core cases, the combined `simplify` pipeline for the end-to-end ones.
Harness contract as the other suites: PASS requires Spot-verified language
equivalence; expected shapes when given; must-not-change cases guard
against over-firing (a & XFa is NOT Fa; mismatched guards stay put).

Run from project root:
    python3 kr/simplify/testing/test_fold_pass.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr.simplify import simplify
from aut2ltl.kr.simplify.fold_pass import fold_simplify

# (input, expected or None, use_pipeline, note)
CASES = [
    # the eight expansion-law folds
    ("a | XFa", "Fa", False, "F expansion law"),
    ("a & XGa", "Ga", False, "G expansion law"),
    ("b | (a & X(a U b))", "a U b", False, "U expansion law"),
    ("b | (a & X(a W b))", "a W b", False, "W expansion law"),
    ("b & (a | X(a R b))", "a R b", False, "R expansion law"),
    ("b & (a | X(a M b))", "a M b", False, "M expansion law"),
    ("a | F(!a & Xa)", "Fa", False, "first occurrence (F seed, n006)"),
    ("a & G(!a | Xa)", "Ga", False, "induction (G seed, n013)"),
    # negative-literal seeds from the F(a&Xa) dump
    ("!a & G(a | X!a)", "G!a", False, "induction, negated atom (n020)"),
    ("!a | F(a & X!a)", "F!a", False, "first occurrence, negated atom (n023)"),
    # cascades: inner fold enables the outer step fold
    ("!a & X(!a & G(a | X!a))", "G!a", False, "n053: induction then G step"),
    ("a & X(a & G(!a | Xa))", "Ga", False, "n040: induction then G step"),
    ("a | X(a | F(!a & Xa))", "Fa", False, "n009: first-occ then F step"),
    # extra siblings survive untouched
    ("d | a | XFa", "d | Fa", False, "fold pair inside a wider Or"),
    ("Gd & a & XGa", "Gd & Ga", False, "fold pair inside a wider And"),
    # BDD tier: boolean c, NNF'd negation
    ("(a & b) | F((!a | !b) & X(a & b))", "F(a & b)", False,
     "first occurrence, boolean c via BDD complement"),
    # multi-conjunct f in the U fold
    ("b | (p & q & X((p & q) U b))", "(p & q) U b", False,
     "U expansion, conjunctive left arm"),
    # S1/S2 sibling subsumption (the Formula-5 line redundancy)
    ("a | X(a R b) | G(a | Xb)", "a | X(a R b)", False,
     "S1: G line subsumed by the R line"),
    ("a & X(a U b) & F(a & Xb)", "a & X(a U b)", False,
     "S2: F conjunct subsumed by the U line"),
    # G/F absorption (Gφ = φ ∧ XGφ as an entailment oracle)
    ("Fb & G(a & Fb)", "G(a & Fb)", False, "G absorbs implied F sibling"),
    ("XFb & G(a & Fb)", "G(a & Fb)", False, "G absorbs through X"),
    ("GFb & G(a & Fb)", "G(a & Fb)", False, "G absorbs derived G"),
    ("Gb | F(a | Gb)", "F(a | Gb)", False, "F absorbs implying G disjunct"),
    ("X(b U a) | F(a | Gb)", "F(a | Gb)", False, "F absorbs X(U) via arm"),
    # context-aware S1/S2 (initial-state knowledge discharges the bare-c
    # case; the same shapes WITHOUT context are not redundant)
    ("!a & (X(a R c) | G(a | Xc))", "!a & X(a R c)", True,
     "ctx-S1: G dropped under !a"),
    ("!a & (X(a | X(a R c)) | G(a | X(a | Xc)))", "!a & X(a | X(a R c))",
     True, "ctx-S1 shifted (the per-level ladder shape)"),
    ("a & ((X(a U c) & F(a & Xc)) | d)", "a & (X(a U c) | d)", True,
     "ctx-S2: F dropped under a"),
    ("a & (d | (X(a & X(a U c)) & F(a & X(a & Xc))))",
     "a & (d | X(a & X(a U c)))", True, "ctx-S2 shifted"),
    # U/R/W arm-padding removal (the census-class-probe pattern)
    ("(q & !r & X(q | r)) U (q & !r & Xr)", "(q & !r) U (q & !r & Xr)",
     False, "U arm unpad: Xd implied by the U dynamics"),
    ("(q & !r & X(q | r)) W (q & !r & Xr)", "(q & !r) W (q & !r & Xr)",
     False, "W arm unpad"),
    ("(!q | r | X(!q & !r)) R (!q | r | X(!r))", "(!q | r) R (!q | r | X(!r))",
     False, "R arm unpad (dual conditions)"),
    # through the full pipeline
    ("c & (a | XFa) & (!c | a | XFa)", "c & Fa", True,
     "pipeline: context dedup + fold"),
    # must not change: these are NOT instances
    ("a & XFa", None, False, "And over F step (must not change)"),
    ("!a | XFa", None, False, "guard mismatch (must not change)"),
    ("b | (a & X(a U c))", None, False, "U arms mismatch (must not change)"),
    ("a | F(a & Xa)", None, False, "not the negation (must not change)"),
    ("a | X(a M b) | G(a | Xb)", None, False,
     "S1 with M is UNSOUND (must not change)"),
    ("a & X(a W b) & F(a & Xb)", None, False,
     "S2 with W is UNSOUND (must not change)"),
    ("X(a | X(a R c)) | G(a | X(a | Xc))", None, True,
     "shifted S1 WITHOUT context is unsound (must not change)"),
    ("Fb & G(a | Fb)", None, False,
     "G body is Or, no entailment (must not change)"),
    ("b & G(a & Fb)", None, False,
     "bare b not implied by G (must not change)"),
    ("(q & Xq) U r", None, False,
     "arm unpad needs g=>d too (must not change; witness q!r;cycle{!q r})"),
]

MUST_NOT_CHANGE = {"a & XFa", "!a | XFa", "b | (a & X(a U c))", "a | F(a & Xa)",
                   "a | X(a M b) | G(a | Xb)", "a & X(a W b) & F(a & Xb)",
                   "X(a | X(a R c)) | G(a | X(a | Xc))",
                   "Fb & G(a | Fb)", "b & G(a & Fb)", "(q & Xq) U r"}


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
        out = simplify(f) if use_pipeline else fold_simplify(f)
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
