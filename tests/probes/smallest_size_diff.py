"""Find the SMALLEST input where two survey runs both produce an LTL formula but of
DIFFERENT size — i.e. a traceable size divergence, not a timeout/decline gap.

Use: locate the smallest case where a recipe blows up under one setting (e.g.
KR_TRANSLATE_INPROC_TEMPORAL_LIMIT unset) vs another (=0), small enough to trace.

    python3 -m tests.probes.smallest_size_diff LEFT.csv RIGHT.csv [--limit N]

Keyed on `source`. Rows are kept only when BOTH sides are result==LTL with a
numeric, DIFFERING dag; sorted by max(dagL, dagR) ascending (smallest first), so the
first rows are the smallest traceable divergences. Prints source, dag pair, and both
formulas.
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Tuple

import pandas as pd


def _load(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    return df.drop_duplicates(subset="source", keep="last").set_index("source")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("left")
    ap.add_argument("right")
    ap.add_argument("--limit", type=int, default=8, help="how many smallest to show")
    args = ap.parse_args()

    L, R = _load(args.left), _load(args.right)
    rows: List[Tuple[int, int, str, str, str, str]] = []
    for src in set(L.index) & set(R.index):
        lo, ro = L.loc[src], R.loc[src]
        if lo.get("result") != "LTL" or ro.get("result") != "LTL":
            continue
        try:
            dl, dr = int(float(lo["dag"])), int(float(ro["dag"]))
        except (ValueError, KeyError):
            continue
        if dl == dr:
            continue
        rows.append((max(dl, dr), dl, dr, src, lo.get("formula", ""), ro.get("formula", "")))

    rows.sort()
    print(f"both-LTL dag-differ rows: {len(rows)}   (smallest {min(args.limit, len(rows))} shown)")
    print(f"left ={args.left}\nright={args.right}\n")
    for mx, dl, dr, src, fl, fr in rows[: args.limit]:
        print(f"[max {mx:>4}]  {src}")
        print(f"    L dag={dl:<4} {fl}")
        print(f"    R dag={dr:<4} {fr}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
