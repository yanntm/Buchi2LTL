#!/usr/bin/env python3
"""
kr/testing/test_kr_basic.py

Minimal direct test using the *normal path* (direct calls to decompose + reconstruct).

- I/O validation: print produced LTL, levels, basic equiv check.
- Failing tests are fine; they focus development.
- Not lots of code in the test itself (the logic lives in kr/).
- Wraps each case invocation in subprocess to detect segfaults (rc 139 / -11 etc.).

Run:
  python3 kr/testing/test_kr_basic.py
  python3 kr/testing/test_kr_basic.py FGa "a U b"   # test specific formulas

See also test_kr_reconstruct.py (for clean vs heuristic side-by-side) and diag_stability.py.
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CASES = [
    "true",
    "false",
    "a",
    "Fa",
    "Ga",
    "Xa",
    "G(p -> X q)",
    "G(p -> (q U r))",
]


def run_case(formula: str) -> None:
    """Run one case in a subprocess (normal path inside child) and report I/O + segv."""
    child_code = f'''
import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"{PROJECT_ROOT}").resolve()))
import spot
from kr import decompose_aut, reconstruct_ltl_1level_buchi as rec_clean

fs = {formula!r}
try:
    f = spot.formula(fs)
    aut = f.translate("Buchi", "Deterministic")
    casc = decompose_aut(aut)
    ltl = rec_clean(casc)
    print("LTL:", ltl)
    print("LEVELS:", casc.num_levels)
    print("ACC_CFGS:", len(casc.accepting_configs()))
    # Basic I/O check + equiv (failing OK)
    try:
        if ltl in ("true", "false", "1", "0"):
            other = spot.formula("true" if ltl in ("true","1") else "false")
        else:
            other = spot.formula(ltl).translate("Buchi")
        orig = f.translate("Buchi")
        print("EQUIV:", bool(spot.are_equivalent(orig, other)))
    except Exception as e:
        print("EQUIV_ERR:", str(e)[:100])
except Exception as e:
    print("ERR:", type(e).__name__, str(e)[:120])
'''
    proc = subprocess.run(
        [sys.executable, "-c", child_code],
        capture_output=True,
        text=True,
        timeout=45,
        cwd=PROJECT_ROOT,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    printed = False
    for line in out.splitlines():
        line = line.strip()
        if line.startswith(("LTL:", "LEVELS:", "EQUIV:", "ERR:", "ACC_CFGS:")):
            print(f"  {formula}: {line}")
            printed = True
    if proc.returncode in (139, -11):
        print(f"  {formula}: SEGV detected (rc={proc.returncode})")
    elif proc.returncode != 0 and not printed:
        print(f"  {formula}: rc={proc.returncode} (no LTL output)")
    elif not printed:
        print(f"  {formula}: (no matching output lines)")


def main():
    parser = argparse.ArgumentParser(
        description="KR basic direct test (normal path + I/O + segv wrap). "
                    "Pass formulas on command line to test specific ones."
    )
    parser.add_argument(
        "formulas", nargs="*", default=None,
        help="Formulas to test (e.g. FGa 'a U b'). If omitted, uses built-in CASES list."
    )
    args = parser.parse_args()

    if args.formulas:
        cases = args.formulas
    else:
        cases = CASES

    print("=== KR basic direct test (normal path + I/O + segv wrap) ===")
    print(f"Project root: {PROJECT_ROOT}")
    print("Cases (direct calls inside wrapped subproc):")
    for fs in cases:
        run_case(fs)
    print()
    print("Done. Use output + EQUIV to focus dev. Failures expected.")


if __name__ == "__main__":
    main()
