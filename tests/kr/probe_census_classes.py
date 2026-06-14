#!/usr/bin/env python3
"""
kr/testing/probe_census_classes.py

How many LANGUAGE equivalence classes does the distinct-temporal census of
a reconstructed formula contain? The census (one Couvreur acc set per
distinct temporal subformula) counts syntactic variants; if the class
count is much smaller, semantic interning (one representative per
future-class) collapses the census at the source.

Method: collect distinct U/M/R/W/F/G nodes; translate each (size-capped,
skip giants); bucket by (state count, acc) of the minimized automaton;
within a bucket, union-find with pairwise spot.are_equivalent. Reports
census vs classes, the largest classes with members, and the per-formula
skip count.

Run from project root (small budget per case):
    python3 kr/testing/probe_census_classes.py "F(a & Xb)" [size_cap]
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr import decompose_aut
from aut2ltl.kr.reachability import reconstruct_ltl_paper_style

TEMPORAL_KINDS = ("U", "M", "R", "W", "F", "G")


def tree_size(f, memo):
    if f in memo:
        return memo[f]
    t = 1 + sum(tree_size(c, memo) for c in f)
    memo[f] = t
    return t


def main():
    formula_str = sys.argv[1] if len(sys.argv) > 1 else "F(a & Xb)"
    size_cap = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    f = spot.formula(formula_str)
    casc = decompose_aut(f.translate())
    root = reconstruct_ltl_paper_style(casc)

    seen, stack, temporal = set(), [root], []
    while stack:
        g = stack.pop()
        if g in seen:
            continue
        seen.add(g)
        if g.kindstr() in TEMPORAL_KINDS:
            temporal.append(g)
        stack.extend(g)

    memo = {}
    small = [t for t in temporal if tree_size(t, memo) <= size_cap]
    skipped = len(temporal) - len(small)
    print(f"=== census classes for '{formula_str}' ===")
    print(f"distinct temporal nodes: {len(temporal)} "
          f"(size cap {size_cap}: {len(small)} checked, {skipped} skipped)")

    t0 = time.monotonic()
    buckets = {}
    auts = {}
    for t in small:
        try:
            a = spot.translate(t, "small", "low")
            key = (a.num_states(), a.num_sets(), a.prop_weak().__bool__())
        except Exception:
            key = ("ERR",)
        auts[t] = None
        buckets.setdefault(key, []).append(t)

    # union-find within buckets
    parent = {t: t for t in small}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    checks = 0
    for key, members in buckets.items():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                if find(a) == find(b):
                    continue
                checks += 1
                try:
                    if spot.are_equivalent(a, b):
                        parent[find(b)] = find(a)
                except Exception:
                    pass

    classes = {}
    for t in small:
        classes.setdefault(find(t), []).append(t)
    elapsed = time.monotonic() - t0

    print(f"language classes among checked: {len(classes)} "
          f"({checks} pairwise checks, {elapsed:.1f}s)")
    print(f"census -> classes: {len(temporal)} -> {len(classes) + skipped} "
          f"(skipped count as singletons)")
    sized = sorted(classes.values(), key=len, reverse=True)
    print("\nlargest classes (representative := members):")
    for cls in sized[:8]:
        if len(cls) < 2:
            break
        rep = min(cls, key=lambda t: tree_size(t, memo))
        print(f"  [{len(cls)}x] {str(rep)[:70]}")
        for m in cls:
            if m != rep:
                print(f"        == {str(m)[:70]}")


if __name__ == "__main__":
    main()
