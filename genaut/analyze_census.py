"""
genaut/analyze_census.py — re-aggregate the committed census CSV (logs/genaut.csv)
for the research-log measurements that are pure CSV reads (no tool re-run):

  Entry 1 — over the LTL-built rows: distinct reconstructed-formula count and the
            idiom histogram (the `reconstructed` column is the truncated formula).
  Entry 2 — the count of universal ("true") survivors (reconstructed == "1").
  Entry 4 — over the true rows: which portfolio technique produced them, and the
            build-time stats.

The "LTL built" partition mirrors tests/survey.py::_report exactly (an answer is
any row whose equiv verdict is in _ANSWER_CATS; not-LTL / timeouts / declines are
not answers). Run after a survey refresh to refresh the log numbers.

Usage:  python3 genaut/analyze_census.py [TOP_N]   # default TOP_N=15
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter
from typing import Dict, List

HERE = os.path.dirname(__file__)
CSV_PATH = os.path.join(HERE, "logs", "genaut.csv")

# An ANSWER (LTL formula built) — same set tests/survey.py uses.
_ANSWER_EQUIV = {"True", "FALSE", "SPOT_TIMEOUT", "UNVERIFIED_SIZE"}


def _is_answer(equiv: str) -> bool:
    return equiv in _ANSWER_EQUIV or equiv.startswith("SPOT_ERR")


def _load() -> List[Dict[str, str]]:
    with open(CSV_PATH, newline="") as fh:
        return list(csv.DictReader(fh))


def main(top_n: int) -> None:
    rows = _load()
    built = [r for r in rows if _is_answer((r.get("equiv") or "").strip())]
    true_rows = [r for r in built if (r.get("reconstructed") or "").strip() == "1"]

    print(f"census CSV: {CSV_PATH}")
    print(f"total rows: {len(rows)}   LTL built: {len(built)}   "
          f"true (reconstructed=='1'): {len(true_rows)}")

    # --- Entry 1: distinct formulas + idiom histogram over the built rows ---
    forms = Counter((r.get("reconstructed") or "").strip() for r in built)
    print(f"\n[Entry 1] distinct reconstructed formulas (truncated): {len(forms)}")
    print(f"          top {top_n} idioms:")
    for form, n in forms.most_common(top_n):
        print(f"            {n:5d}  {form!r}")

    # --- Entry 4: technique routes + build-time over the true rows ---
    techs = Counter((r.get("technique") or "").strip() for r in true_rows)
    builds = [float(r.get("build_s") or 0.0) for r in true_rows]
    print(f"\n[Entry 4] technique routes to `true` ({len(true_rows)} rows):")
    for tech, n in techs.most_common():
        print(f"            {n:5d}  {tech}")
    if builds:
        total = sum(builds)
        print(f"          build_s: total {total:.1f}s  mean {total/len(builds):.3f}s  "
              f"max {max(builds):.3f}s")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    main(n)
