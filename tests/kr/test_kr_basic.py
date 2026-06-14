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

See also test_kr_reconstruct.py (paper path verification) and diag_stability.py.

Note: decompose_aut now normalizes internally to deterministic minimized parity
complete automata (per paper); the test translate() calls are intentionally loose.
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
from aut2ltl.kr import decompose_aut, reconstruct_bls as rec_clean

fs = {formula!r}
import sys
print("CHILD_START:", fs, flush=True)
try:
    f = spot.formula(fs)
    print("CHILD_FORMULA_OK", flush=True)
    aut = f.translate()
    print("CHILD_TRANSLATE_OK states=", aut.num_states(), flush=True)
    casc = decompose_aut(aut)
    ltl = rec_clean(casc)   # spot.formula DAG (never implicitly flattened)
    from aut2ltl.kr.ltl_builders import _str_f_gated
    print("LTL:", _str_f_gated(ltl))
    print("LEVELS:", casc.num_levels)
    print("ACC_CFGS:", len(casc.accepting_configs()))
    try:
        import aut2ltl.kr.reachability_operators as _ops
        print("REACH_CALLS:", getattr(_ops, 'PAPER_REACH_CALLS', -1))
        print("FIN_CALLS:", getattr(_ops, 'PAPER_FIN_CALLS', -1))
        print("MAXSZ:", getattr(_ops, 'PAPER_MAX_LTL_SIZE', -1))
    except Exception as _e:
        print("COUNTER_ERR:", _e)
    # Basic I/O check + equiv (failing OK) — translate straight from the object
    try:
        other = ltl.translate("Buchi")
        orig = f.translate("Buchi")
        print("EQUIV:", bool(spot.are_equivalent(orig, other)))
    except Exception as e:
        print("EQUIV_ERR:", str(e)[:100])
except Exception as e:
    import traceback
    print("ERR:", type(e).__name__, str(e)[:120])
    print("TRACEBACK:", traceback.format_exc()[:800])
'''
    out = ""
    err = ""
    rc = None
    try:
        proc = subprocess.run(
            [sys.executable, "-c", child_code],
            capture_output=True,
            text=True,
            timeout=45,
            cwd=PROJECT_ROOT,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        rc = proc.returncode
    except subprocess.TimeoutExpired as te:
        so = te.stdout or b""
        se = te.stderr or b""
        if isinstance(so, (bytes, bytearray)):
            so = so.decode("utf-8", errors="replace")
        if isinstance(se, (bytes, bytearray)):
            se = se.decode("utf-8", errors="replace")
        out = so + se
        err = str(te)
        rc = 124  # conventional timeout rc
    printed = False
    for line in out.splitlines():
        line = line.strip()
        if line.startswith(("LTL:", "LEVELS:", "EQUIV:", "ERR:", "ACC_CFGS:", "REACH_CALLS:", "FIN_CALLS:", "MAXSZ:", "COUNTER_ERR:", "TRACEBACK:")):
            print(f"  {formula}: {line}")
            printed = True
    if rc in (139, -11):
        print(f"  {formula}: SEGV detected (rc={rc})")
    elif rc == 124:
        print(f"  {formula}: TIMEOUT (5s) - partial child output above (if any). Likely hang/loop in decomp or rec.")
        if err:
            print(f"  {formula}: TIMEOUT_DETAIL: {err[:100]}")
    elif rc != 0 and not printed:
        print(f"  {formula}: rc={rc} (no LTL output)")
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
