#!/usr/bin/env python3
"""
survey/diff/diff_hoa.py — directional language diff of an HOA automaton FILE against
an LTL formula, with witness words. The CLI of `ltl_diff.py` parses both args as
LTL strings, so it cannot take a `.hoa`/`.txt` automaton path; this wraps the
same `diff_report` after loading the automaton with spot.

Usage:
    python3 -m survey.diff.diff_hoa <hoa-file> "<ltl-formula>"
"""
import sys

import spot
from survey.diff import diff_report

def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip())
        return 2
    hoa_path, formula = sys.argv[1], sys.argv[2]
    aut = spot.automaton(hoa_path)
    print(f"GT = {hoa_path}")
    print(f"produced = {formula}")
    print(diff_report(aut, formula, "GT", "produced"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
