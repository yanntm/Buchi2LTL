#!/usr/bin/env python3
"""
Gate test for survey.diff.results: the consistency tier (FAIL / CLASH) sets a
non-zero exit, while purely quantitative differences (size / timeout / fewer
answers) do NOT. Synthesises small CSV pairs and checks main()'s return code.

    python3 tests/probes/test_diff_results.py
"""
import csv
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

import survey.diff.results as R

COLS: List[str] = ["input", "result", "technique", "build_s", "formula",
                   "dag", "temporals", "tree", "sharing", "md5", "validation",
                   "source"]
_fail: List[str] = []


def check(cond: bool, msg: str) -> None:
    print(("ok  " if cond else "FAIL") + " : " + msg)
    if not cond:
        _fail.append(msg)


def _row(source: str, result: str, validation: str, dag: int) -> Dict[str, str]:
    r = {c: "" for c in COLS}
    r.update(input=source, source=source, result=result, technique="t",
             validation=validation, dag=str(dag), tree=str(dag))
    return r


def _write(path: Path, rows: List[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)


def _diff_exit(left: Path, right: Path) -> int:
    argv = sys.argv
    sys.argv = ["results", str(left), str(right)]
    try:
        return R.main()
    finally:
        sys.argv = argv


def main() -> int:
    base = [_row("s1", "LTL", "TRUE", 5), _row("s2", "LTL", "TRUE", 10)]
    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        _write(dp / "base.csv", base)

        # OK: same verdicts, only a size blow-up on s2 (quantitative only).
        _write(dp / "bigger.csv",
               [_row("s1", "LTL", "TRUE", 5), _row("s2", "LTL", "TRUE", 99999)])
        check(_diff_exit(dp / "base.csv", dp / "bigger.csv") == 0,
              "size blow-up alone -> exit 0 (quantitative, not a regression)")

        # OK: a TRUE -> TIMEOUT validation move (oracle couldn't verify) is NOT a fail.
        _write(dp / "timeout.csv",
               [_row("s1", "LTL", "TRUE", 5), _row("s2", "LTL", "TIMEOUT", 10)])
        check(_diff_exit(dp / "base.csv", dp / "timeout.csv") == 0,
              "TRUE -> TIMEOUT move -> exit 0 (unverified, not a fail)")

        # FAIL: a verified non-equivalent on one side gates.
        _write(dp / "fail.csv",
               [_row("s1", "LTL", "FAIL", 5), _row("s2", "LTL", "TRUE", 10)])
        check(_diff_exit(dp / "base.csv", dp / "fail.csv") == 1,
              "FAIL on a common input -> exit 1 (correctness gate)")

        # CLASH: one run says LTL, the other NOT_LTL on the same input.
        _write(dp / "clash.csv",
               [_row("s1", "LTL", "TRUE", 5), _row("s2", "NOT_LTL", "", 0)])
        check(_diff_exit(dp / "base.csv", dp / "clash.csv") == 1,
              "LTL vs NOT_LTL on a common input -> exit 1 (correctness gate)")

    if _fail:
        print(f"\n{len(_fail)} FAILED")
        return 1
    print("\nall ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
