#!/usr/bin/env python3
"""
kr/testing/ltl_diff.py

Directional language comparison of two LTL formulas (or a formula vs an
automaton), with witness words. Far more useful for debugging than a bare
are_equivalent boolean:

  - A <= B ? (every word of A is in B)
  - B <= A ?
  - For each failing containment, a concrete witness word (lasso) in the
    difference, via spot.difference(X, Y).accepting_word().

Usage:
    python3 kr/testing/ltl_diff.py "GFa" "!a R (a | (!a & XFa))"

Library use (from other kr/testing scripts):
    from ltl_diff import diff_report, to_aut
    print(diff_report(aut_or_formula_A, aut_or_formula_B, "GT", "produced"))
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot


def to_aut(x):
    """Accept an LTL string, spot.formula, or twa; return a Buchi twa."""
    if isinstance(x, str):
        x = spot.formula(x)
    if isinstance(x, spot.formula):
        return x.translate("Buchi")
    return x


def diff_report(a, b, name_a: str = "A", name_b: str = "B") -> str:
    """Compare languages of a and b; return a multi-line report with
    containment verdicts and witness words for each strict difference."""
    aut_a, aut_b = to_aut(a), to_aut(b)
    a_in_b = spot.contains(aut_b, aut_a)   # contains(big, small): small <= big
    b_in_a = spot.contains(aut_a, aut_b)

    lines = []
    if a_in_b and b_in_a:
        lines.append(f"  {name_a} == {name_b} (languages equivalent)")
        return "\n".join(lines)

    if a_in_b:
        lines.append(f"  {name_a} STRICTLY INSIDE {name_b} ({name_b} over-approximates)")
    elif b_in_a:
        lines.append(f"  {name_b} STRICTLY INSIDE {name_a} ({name_b} under-approximates)")
    else:
        lines.append(f"  {name_a} and {name_b} are INCOMPARABLE")

    if not a_in_b:
        w = spot.product(aut_a, spot.complement(aut_b)).accepting_word()
        lines.append(f"  witness in {name_a} \\ {name_b}: {w}")
    if not b_in_a:
        w = spot.product(aut_b, spot.complement(aut_a)).accepting_word()
        lines.append(f"  witness in {name_b} \\ {name_a}: {w}")
    return "\n".join(lines)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    fa, fb = sys.argv[1], sys.argv[2]
    print(f"A: {fa}")
    print(f"B: {fb}")
    print(diff_report(fa, fb, "A", "B"))


if __name__ == "__main__":
    main()
