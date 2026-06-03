#!/usr/bin/env python3
"""
kr/testing/diag_stability.py

Repeated decomposition stability test.

Historically, certain formulas (especially "Xa" which produces a 3-level cascade
with the dead-trap state, and others with |AP|>=1) would cause sporadic
segfaults (exit 139) inside the Spot/buddy C extensions during
extract_generators (the _valuation_to_bdd hack that discovered buddy var ids
by creating many tiny auts *interleaved* with bdd & operations on the main aut).

Fix: kr/bdd_utils.py now does get_ap_bdd_vars(aut) *once* before the letter loop,
then re-uses the map for every point_bdd. This eliminates the interleaving hazard.

This script runs the problematic cases multiple times in isolated subprocesses
and reports any SEGV.

Run:
    python3 kr/testing/diag_stability.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

REPEAT = 4
PROBLEMATIC = ["Xa", "a", "G(p -> (q U r))", "G(p -> X q)"]


def decomp_once(formula_str: str) -> tuple[int, str]:
    """Decompose in a fresh child process. Return (returncode, short_output)."""
    code = f'''
import sys
from pathlib import Path
proj = Path(r"{PROJECT_ROOT}").resolve()
sys.path.insert(0, str(proj))
import spot
from kr import decompose_aut
f = spot.formula({formula_str!r})
aut = f.translate("Buchi", "Deterministic")
casc = decompose_aut(aut)
print(f"OK lvls={{casc.num_levels}} n={{casc.num_states}}")
'''
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=PROJECT_ROOT,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()[:120]


def main():
    print("=== KR decomposition stability diag (repeated, isolated) ===")
    print(f"Repeating each of {PROBLEMATIC} x {REPEAT} times...")
    print()

    failures = []
    for fs in PROBLEMATIC:
        print(f"--- {fs} ---")
        for i in range(1, REPEAT + 1):
            rc, out = decomp_once(fs)
            if rc == 139:
                print(f"  iter {i}: SEGV (139)")
                failures.append((fs, i))
            elif rc != 0:
                print(f"  iter {i}: rc={rc} out={out}")
            else:
                print(f"  iter {i}: {out}")
        print()

    if failures:
        print("FAILURES:")
        for fs, i in failures:
            print(f"  {fs} iter {i}")
        sys.exit(1)
    else:
        print("All runs succeeded with no segfaults.")
        print("Stability improvement (bdd_utils precompute) appears effective.")


if __name__ == "__main__":
    main()
