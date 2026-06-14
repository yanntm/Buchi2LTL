#!/usr/bin/env python3
"""
kr/testing/measure_formula_dag.py

Measure the assembled paper-style formula as a hash-consed DAG vs its flat
serialization: distinct subformula nodes, tree (unfolded) node count, string
length, count of distinct U/M/R/W (acceptance-relevant) subformulas, and
construction wall time. This quantifies the post-step-1 state: the operators
now build shared spot.formula objects end-to-end, so the interesting numbers
are DAG size (real complexity) vs string size (unfolded form).

Run from project root:
    python3 kr/testing/measure_formula_dag.py "G(a -> X b)"
    python3 kr/testing/measure_formula_dag.py "G(a -> X b)" --out out.ltl
                                  (also dump the flat formula string to a file,
                                   re-parsed afterwards as a sanity check)
"""

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr import decompose_aut
import aut2ltl.kr.reachability_operators as _ops
from aut2ltl.kr.reachability import reconstruct_ltl_paper_style
# reconstruct now returns the spot.formula DAG itself (no final str), so this
# tool measures the REAL pipeline output — the former local re-implementation
# of the Muller-DNF assembly is gone.


def dag_stats(f: "spot.formula") -> dict:
    """Traverse the formula sharing-aware (seen-set on node ids)."""
    seen = set()
    stack = [f]
    n_unique = 0
    kinds = {}
    while stack:
        g = stack.pop()
        gid = g.id()
        if gid in seen:
            continue
        seen.add(gid)
        n_unique += 1
        k = g.kindstr()
        kinds[k] = kinds.get(k, 0) + 1
        for child in g:
            stack.append(child)
    return {"unique_nodes": n_unique, "kinds": kinds}


def tree_size(f: "spot.formula", limit: int = 50_000_000) -> int:
    """Unfolded (tree) node count, memoized per shared node."""
    memo = {}

    def rec(g):
        gid = g.id()
        if gid in memo:
            return memo[gid]
        total = 1
        for child in g:
            total += rec(child)
            if total > limit:
                break
        memo[gid] = total
        return total

    return rec(f)


def main():
    parser = argparse.ArgumentParser(description="DAG vs string measurement of the assembled paper-style formula.")
    parser.add_argument("formula", nargs="?", default="G(a -> X b)")
    parser.add_argument("--out", help="write the flat formula string to this file (parse-checked after writing)")
    parser.add_argument("--no-str", action="store_true",
                        help="skip flat stringification entirely (the unfolded "
                             "string can be 100MB+ while the DAG stays tiny)")
    args = parser.parse_args()
    formula_str = args.formula
    print(f"=== DAG measurement for '{formula_str}' ===")
    f = spot.formula(formula_str)
    casc = decompose_aut(f.translate())
    print(f"cascade: {casc.num_levels} levels, sizes={[l.size for l in casc.levels]}")

    t0 = time.monotonic()
    res_f = reconstruct_ltl_paper_style(casc)   # resets counters/memos itself
    t_build = time.monotonic() - t0

    stats = dag_stats(res_f)
    n_tree = tree_size(res_f)
    if args.no_str:
        s, t_str = "", 0.0
    else:
        t1 = time.monotonic()
        s = str(res_f)
        t_str = time.monotonic() - t1

    acc_relevant = sum(v for k, v in stats["kinds"].items()
                       if k in ("U", "M", "R", "W", "F", "G"))
    print(f"construction time         : {t_build:.2f}s "
          f"(reach_calls={_ops.PAPER_REACH_CALLS}, fin_calls={_ops.PAPER_FIN_CALLS})")
    print(f"DAG unique nodes          : {stats['unique_nodes']}")
    print(f"tree (unfolded) nodes     : {n_tree}")
    if args.no_str:
        print("string length             : SKIPPED (--no-str)")
    else:
        print(f"string length             : {len(s)} (str() took {t_str:.2f}s)")
    print(f"sharing factor (tree/DAG) : {n_tree / max(stats['unique_nodes'], 1):.1f}x")
    print(f"distinct temporal binaries (U/M/R/W/F/G): {acc_relevant}")
    print("node kinds:", dict(sorted(stats["kinds"].items(), key=lambda kv: -kv[1])))

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(s + "\n", encoding="utf-8")
        reparsed = spot.formula(out_path.read_text(encoding="utf-8").strip())
        same = (reparsed == res_f)
        print(f"formula written to        : {out_path} ({out_path.stat().st_size} bytes; "
              f"parse-back == built object: {same})")


if __name__ == "__main__":
    main()
