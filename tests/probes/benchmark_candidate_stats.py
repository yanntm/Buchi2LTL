"""tests/probes/benchmark_candidate_stats.py — README-example candidate finder.

Scan a survey CSV for verified LTL-input rows whose INPUT formula is chunky but
whose reconstructed OUTPUT is short (within the print cutoff), and for each build
the input automaton with `ltl2tgba --small` (spot.translate tgba/small) and
tabulate its shape: states, SCCs, #AP, #acceptance sets, acceptance condition.

Usage:
  python3 tests/probes/benchmark_candidate_stats.py [TOP] [MAX_OUT]
    TOP      number of candidates to show, by input length desc (default 20)
    MAX_OUT  keep only rows whose output formula is shorter than this (default 20)
"""
from __future__ import annotations

import csv
import sys
from typing import Dict, List

import spot

CSV = "results/reference/benchmark/default.csv"


def _candidates(max_out: int) -> List[Dict[str, str]]:
    """Verified LTL-input rows with a short, fully-printed output formula."""
    rows: List[Dict[str, str]] = []
    with open(CSV, newline="") as fh:
        for r in csv.DictReader(fh):
            out = r["formula"]
            if (".ltl:" in r["source"] and r["validation"] == "TRUE"
                    and 0 < len(out) < max_out
                    and "unflattened" not in out and "…" not in out):
                rows.append(r)
    rows.sort(key=lambda r: len(r["input"]), reverse=True)
    return rows


def main(top: int, max_out: int) -> None:
    cands = _candidates(max_out)[:top]
    hdr = (f"{'in':>3} {'out':>3} {'st':>3} {'scc':>3} {'ap':>3} {'acc':>3}  "
           f"{'acceptance':<14} input -> output")
    print(hdr)
    print("-" * len(hdr))
    agg: Dict[str, List[int]] = {"st": [], "scc": [], "ap": [], "acc": []}
    for r in cands:
        a = spot.translate(spot.formula(r["input"]), "tgba", "small")
        st, scc = a.num_states(), spot.scc_info(a).scc_count()
        ap, nacc = len(a.ap()), a.acc().num_sets()
        for k, v in (("st", st), ("scc", scc), ("ap", ap), ("acc", nacc)):
            agg[k].append(v)
        print(f"{len(r['input']):>3} {len(r['formula']):>3} {st:>3} {scc:>3} {ap:>3} "
              f"{nacc:>3}  {str(a.get_acceptance()):<14} {r['input']}  ->  {r['formula']}")
    n = len(cands) or 1
    print("-" * len(hdr))
    for k, label in (("st", "states"), ("scc", "scc"), ("ap", "ap"), ("acc", "acc")):
        v = agg[k] or [0]
        print(f"{label:>7}: min {min(v)} / max {max(v)} / mean {sum(v)/n:.1f}")


if __name__ == "__main__":
    top = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    max_out = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    main(top, max_out)
