#!/usr/bin/env python3
"""
kr/testing/probe_dag_dump.py

Readable full expansion of one reconstructed formula: print the hash-consed
DAG as let-bindings (every shared-or-large node gets a name, definitions in
bottom-up topological order, small nodes inlined), then the census of
distinct temporal subformulas sorted by unfolded size. The view for hunting
new fold/rewrite rules on a case that still explodes.

Run from project root:
    python3 kr/testing/probe_dag_dump.py "F(a & Xb)"
    python3 kr/testing/probe_dag_dump.py "F(a & Xb)" --inline-len 40
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr import decompose_aut
from aut2ltl.kr.reachability import reconstruct_ltl_paper_style

TEMPORAL_KINDS = ("U", "M", "R", "W", "F", "G")


def walk(root):
    """Post-order over distinct nodes; returns (order, refcounts)."""
    refs = {}
    order = []
    seen = set()
    stack = [(root, False)]
    while stack:
        node, done = stack.pop()
        nid = node.id()
        if done:
            order.append(node)
            continue
        refs[nid] = refs.get(nid, 0) + 1
        if nid in seen:
            continue
        seen.add(nid)
        stack.append((node, True))
        for child in node:
            stack.append((child, False))
    return order, refs


def main():
    parser = argparse.ArgumentParser(description="let-binding dump of the reconstructed formula DAG")
    parser.add_argument("formula", nargs="?", default="F(a & Xb)")
    parser.add_argument("--inline-len", type=int, default=30,
                        help="nodes whose rendered form is at most this long are inlined (default 30)")
    args = parser.parse_args()

    f = spot.formula(args.formula)
    casc = decompose_aut(f.translate())
    print(f"=== DAG dump for '{args.formula}' ===")
    print(f"cascade: {casc.num_levels} levels, sizes={[l.size for l in casc.levels]}")
    root = reconstruct_ltl_paper_style(casc)

    order, refs = walk(root)
    print(f"distinct nodes: {len(order)}")

    # Render bottom-up: a node is named when shared or when its rendition is
    # long; otherwise inlined into its parents.
    rendered = {}   # id -> inline text (name or full short form)
    defs = []       # (name, definition text, node)
    names = {}      # id -> name

    def child_text(node):
        return rendered[node.id()]

    for node in order:
        nid = node.id()
        if nid in rendered:
            continue
        k = node.kindstr()
        kids = [child_text(c) for c in node]
        if k == "ap":
            txt = str(node)
        elif k in ("tt", "ff"):
            txt = "1" if k == "tt" else "0"
        elif k == "Not":
            txt = f"!{kids[0]}"
        elif k == "X":
            txt = f"X{kids[0]}" if not kids[0].startswith(("(", "!")) and len(kids[0]) <= 2 else f"X({kids[0]})"
        elif k in ("F", "G"):
            txt = f"{k}({kids[0]})"
        elif k in ("And", "Or"):
            sep = " & " if k == "And" else " | "
            txt = "(" + sep.join(kids) + ")"
        elif k in ("U", "M", "R", "W"):
            txt = f"({kids[0]} {k} {kids[1]})"
        else:
            txt = f"{k}({', '.join(kids)})"

        share = refs.get(nid, 1)
        if len(txt) > args.inline_len or (share > 1 and len(txt) > 8):
            name = f"n{len(defs):03d}"
            names[nid] = name
            defs.append((name, txt, node, share))
            rendered[nid] = name
        else:
            rendered[nid] = txt

    print(f"\n--- definitions ({len(defs)}; xN = referenced N times) ---")
    for name, txt, node, share in defs:
        tag = f" x{share}" if share > 1 else ""
        print(f"{name}{tag} := {txt}")
    print(f"\nroot = {rendered[root.id()]}")

    # Temporal census: every distinct U/M/R/W/F/G node, sorted by tree size.
    memo = {}
    def tsize(g):
        gid = g.id()
        if gid in memo:
            return memo[gid]
        t = 1 + sum(tsize(c) for c in g)
        memo[gid] = t
        return t

    temporal = [n for n in order if n.kindstr() in TEMPORAL_KINDS]
    temporal.sort(key=tsize)
    print(f"\n--- distinct temporal subformulas ({len(temporal)}), by unfolded size ---")
    for n in temporal:
        nid = n.id()
        label = names.get(nid, rendered.get(nid, "?"))
        s = str(n)
        if len(s) > 100:
            s = s[:97] + "..."
        print(f"[{tsize(n):>6}] {n.kindstr():1} x{refs.get(nid,1):<2} {label:>5} : {s}")


if __name__ == "__main__":
    main()
