#!/usr/bin/env python3
"""
kr/simplify/testing/test_random_equiv.py

Random soundness fuzz for the combined kr.simplify.simplify pipeline:
N random LTL formulas (spot.randltl, few APs so the rules actually fire),
each simplified and checked for language equivalence against the original.
Any non-equivalence is a soundness bug and is printed with both formulas.

Also reports fire rate and size deltas (tree nodes before/after), so the
run doubles as a usefulness measurement.

Run from project root:
    python3 kr/simplify/testing/test_random_equiv.py [N] [seed] [n_aps] [tree_size]
Defaults: N=500 seed=42 n_aps=2 tree_size=15.
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr.simplify import simplify


def tree_size(f: "spot.formula") -> int:
    n = 1
    for c in f:
        n += tree_size(c)
    return n


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    n_aps = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    tsize = int(sys.argv[4]) if len(sys.argv) > 4 else 15

    # Oracle self-test: a fuzz whose oracle cannot fail is vacuous.
    assert not spot.are_equivalent(spot.formula("a"), spot.formula("b"))
    assert spot.are_equivalent(spot.formula("a U b"), spot.formula("b | (a & X(a U b))"))

    aps = [chr(ord("a") + i) for i in range(n_aps)]
    gen = spot.randltl(aps, n, seed=seed, tree_size=tsize)

    t0 = time.monotonic()
    total = changed = failures = 0
    sum_before = sum_after = 0
    worst_growth = 0
    for f in gen:
        total += 1
        out = simplify(f)
        b, a = tree_size(f), tree_size(out)
        sum_before += b
        sum_after += a
        worst_growth = max(worst_growth, a - b)
        if out != f:
            changed += 1
        if not spot.are_equivalent(f, out):
            failures += 1
            print(f"  NOT EQUIVALENT:\n    in : {f}\n    out: {out}")
    dt = time.monotonic() - t0

    print(f"\n{total} formulas ({n_aps} APs, tree_size={tsize}, seed={seed}) "
          f"in {dt:.1f}s")
    print(f"  changed       : {changed} ({100.0 * changed / max(total,1):.0f}%)")
    print(f"  tree nodes    : {sum_before} -> {sum_after} "
          f"({100.0 * (sum_before - sum_after) / max(sum_before,1):.1f}% smaller)")
    print(f"  worst growth  : +{worst_growth} nodes")
    print(f"  equivalence   : {'ALL EQUIVALENT' if failures == 0 else f'{failures} FAILURE(S)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
