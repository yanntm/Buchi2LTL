#!/usr/bin/env python3
"""
kr/testing/probe_case_diff.py

Containment direction + witness word for one formula's full roundtrip:
build the cascade, reconstruct (formula DAG), translate BOTH sides from
objects, and run ltl_diff.diff_report. For cases whose flat form cannot
ride argv/JSON (multi-MB) — the in-process object-path version of
`ltl_diff.py orig recovered`.

Run from project root (case must translate within the session budget —
post per-node-simplify this works for e.g. G(a->Xb)):
    python3 kr/testing/probe_case_diff.py "G(a -> X b)"
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from kr import decompose_aut
from kr.reachability import reconstruct_ltl_paper_style

# Diff runs in a FRESH subprocess fed via stdin (multi-MB formulas die on
# argv with E2BIG) — replicating the survey's verification structure, which
# empirically gets past translation where the construction process itself
# trips the 32-acc-set wall.
_DIFF_CHILD = '''
import sys, json
sys.path.insert(0, r"%(testdir)s")
import spot
from ltl_diff import diff_report
p = json.load(sys.stdin)
print(diff_report(spot.formula(p["orig"]), spot.formula(p["rec"]),
                  "original", "recovered"))
''' % {"testdir": str(PROJECT_ROOT / "kr" / "testing")}


def main():
    fs = sys.argv[1] if len(sys.argv) > 1 else "G(a -> X b)"
    budget = int(__import__("os").environ.get("KR_CHECK_TIMEOUT", "10"))
    print(f"=== roundtrip diff for '{fs}' (diff child budget {budget}s) ===")
    f = spot.formula(fs)
    casc = decompose_aut(f.translate())
    rec_f = reconstruct_ltl_paper_style(casc)
    rec_s = str(rec_f)
    print(f"recovered flat: {len(rec_s)} chars")
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _DIFF_CHILD],
            input=json.dumps({"orig": fs, "rec": rec_s}),
            capture_output=True, text=True, timeout=budget, cwd=PROJECT_ROOT)
    except subprocess.TimeoutExpired:
        print(f"DIFF_TIMEOUT >{budget}s (verification blocked, not a verdict)")
        return
    print((proc.stdout or "").rstrip() or ("STDERR: " + (proc.stderr or "")[:400]))


if __name__ == "__main__":
    main()
