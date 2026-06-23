"""tests/probes/aut2ltl_vs_ltlfilt.py — where the semantic route beats syntax.

For each verified LTL-input row in a survey CSV, compare aut2ltl's reconstructed
formula size (the `tree` column) against `ltlfilt -r3`'s best *syntactic*
simplification of the same input. Rank by how much SMALLER aut2ltl is — those are
the README-worthy cases (aut2ltl recovers via the automaton a formula that pure
LTL simplification cannot reach).

One `ltlfilt -r3` subprocess (formulas piped on stdin, order preserved); spot
counts tree nodes in-process.

Usage:
  python3 tests/probes/aut2ltl_vs_ltlfilt.py [TOP]   # default 20
"""
from __future__ import annotations

import csv
import subprocess
import sys
from typing import Dict, List

import spot

CSV = "results/reference/benchmark/default.csv"


def _rows() -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    with open(CSV, newline="") as fh:
        for r in csv.DictReader(fh):
            f = r["formula"]
            if (".ltl:" in r["source"] and r["validation"] == "TRUE"
                    and f and "unflattened" not in f and "…" not in f):
                out.append(r)
    return out


def _ltlfilt_r3(formulas: List[str]) -> List[str]:
    """Run `ltlfilt -r3` once over all formulas (stdin, one per line)."""
    p = subprocess.run(["ltlfilt", "-r3", "-F", "-"], input="\n".join(formulas),
                       capture_output=True, text=True, check=True)
    return p.stdout.splitlines()


def _tree(f: str) -> int:
    return spot.length(spot.formula(f))


def main(top: int) -> None:
    rows = _rows()
    simp = _ltlfilt_r3([r["input"] for r in rows])
    items = []
    for r, s in zip(rows, simp):
        a_tree, l_tree = int(r["tree"]), _tree(s)
        items.append((l_tree - a_tree, l_tree, a_tree, r["input"], s, r["formula"]))
    items.sort(reverse=True)
    print(f"{'gap':>4} {'lf':>3} {'a2l':>3}  input  |  ltlfilt -r3  =>  aut2ltl")
    print("-" * 80)
    for gap, lt, at, inp, lf, a2l in items[:top]:
        print(f"{gap:>4} {lt:>3} {at:>3}  {inp}\n           ltlfilt: {lf}\n           aut2ltl: {a2l}\n")
    wins = sum(1 for it in items if it[0] > 0)
    print(f"aut2ltl strictly smaller than ltlfilt -r3 on {wins}/{len(items)} LTL inputs")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
