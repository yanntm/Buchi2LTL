#!/usr/bin/env python3
"""
kr/testing/compare_sizes.py

Compare two size-census logs (the per-case lines emitted by survey_sizes.py:
"<formula> ... DAG=<n> tree=<n> temporal=<n>") and print the per-case delta in
DAG / tree / distinct-temporal nodes. The temporal column (the 32-acc-cap driver)
is the headline metric.

Robust to either log's section formatting — it scans every line matching
"DAG=.. tree=.. temporal=.." and keys on the formula text before the first
"split=" / "mp=" / "DAG=" token. Cases present in only one log are listed
separately. A win (smaller in B) is marked ↓, a regression ↑.

Run from project root:
    python3 kr/testing/compare_sizes.py OLD.txt NEW.txt
    python3 kr/testing/compare_sizes.py OLD.txt NEW.txt --sort temporal
    python3 kr/testing/compare_sizes.py OLD.txt NEW.txt --only-changed
"""

import re
import sys
from pathlib import Path

_ROW = re.compile(r"DAG=\s*(\d+)\s+tree=\s*(\d+)\s+temporal=\s*(\d+)")


def parse(path: Path) -> dict:
    """formula -> (dag, tree, temporal). Formula = text left of the first
    'mp=' / 'split=' / 'DAG=' marker, stripped."""
    out = {}
    for line in path.read_text().splitlines():
        m = _ROW.search(line)
        if not m:
            continue
        head = line[: m.start()]
        head = re.split(r"\bmp=|\bsplit=", head)[0]
        name = head.strip()
        if not name:
            continue
        out[name] = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return out


def _fmt(n: int) -> str:
    return f"{n:.2e}" if n >= 10**7 else str(n)


def _delta(a: int, b: int) -> str:
    if b == a:
        return "="
    arrow = "↓" if b < a else "↑"
    if a > 0:
        return f"{arrow}{(b - a) / a * 100:+.0f}%"
    return arrow


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    old_p, new_p = Path(args[0]), Path(args[1])
    old, new = parse(old_p), parse(new_p)

    sort_key = "temporal"
    if "--sort" in sys.argv:
        sort_key = sys.argv[sys.argv.index("--sort") + 1]
    idx = {"dag": 0, "tree": 1, "temporal": 2}.get(sort_key, 2)
    only_changed = "--only-changed" in flags

    common = [k for k in old if k in new]
    # sort by absolute temporal (or chosen) delta, biggest mover first
    common.sort(key=lambda k: abs(new[k][idx] - old[k][idx]), reverse=True)

    print(f"OLD = {old_p.name}")
    print(f"NEW = {new_p.name}\n")
    print(f"  {'formula':22s} {'DAG (old→new)':22s} {'tree (old→new)':26s} "
          f"{'temporal (old→new)':22s}")
    print("  " + "-" * 96)
    tot_old = [0, 0, 0]
    tot_new = [0, 0, 0]
    n_down = n_up = 0
    for k in common:
        o, n = old[k], new[k]
        for i in range(3):
            tot_old[i] += o[i]
            tot_new[i] += n[i]
        if n[2] < o[2]:
            n_down += 1
        elif n[2] > o[2]:
            n_up += 1
        if only_changed and o == n:
            continue
        dag = f"{o[0]}→{n[0]} {_delta(o[0], n[0])}"
        tree = f"{_fmt(o[1])}→{_fmt(n[1])} {_delta(o[1], n[1])}"
        tmp = f"{o[2]}→{n[2]} {_delta(o[2], n[2])}"
        print(f"  {k:22s} {dag:22s} {tree:26s} {tmp:22s}")

    only_old = [k for k in old if k not in new]
    only_new = [k for k in new if k not in old]
    if only_old:
        print(f"\n  only in OLD: {', '.join(only_old)}")
    if only_new:
        print(f"\n  only in NEW: {', '.join(only_new)}")

    print(f"\n  === totals over {len(common)} common cases ===")
    print(f"  DAG       {tot_old[0]} → {tot_new[0]}  ({_delta(tot_old[0], tot_new[0])})")
    print(f"  tree      {_fmt(tot_old[1])} → {_fmt(tot_new[1])}  ({_delta(tot_old[1], tot_new[1])})")
    print(f"  temporal  {tot_old[2]} → {tot_new[2]}  ({_delta(tot_old[2], tot_new[2])})")
    print(f"  cases: {n_down} smaller (↓), {n_up} larger (↑), "
          f"{len(common) - n_down - n_up} unchanged")


if __name__ == "__main__":
    main()
