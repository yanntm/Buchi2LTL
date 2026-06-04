#!/usr/bin/env python3
"""
kr/testing/test_kr_reconstruct.py

Verification for the pure paper reconstruction path in kr/:
- decomp (Spot -> det parity complete -> SgpDec cascade)
- reconstruct_ltl_1level_buchi (which uses the inductive reach formulas +
  fin_c (Lemma 7) + Muller DNF assembly from good SCC sets)

Uses subprocess isolation per case (stability: fresh python, no Spot/buddy
state accumulation or segvs). Reports LTL, levels, acc count, and Spot
equivalence where possible.

Failing equiv is expected for some multi-level cases until the 5 formulas
are fully polished for conj/neg/entry per the paper.

Run from project root:
    python3 kr/testing/test_kr_reconstruct.py
    python3 kr/testing/test_kr_reconstruct.py "a" "Fa"   # specific

See also test_kr_basic.py and diag_stability.py.
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from kr import (
    decompose_aut,
    reconstruct_ltl_1level_buchi,
)

# Cases chosen to exercise 0/1/multi level cascades and the paper path.
# Expanded for roundtrip analysis (LTL -> decomp -> pure reconstruct -> Spot equiv).
# Only formulas that survive full algebraic path (no heuristics) are expected to roundtrip.
CASES = [
    "true",
    "false",
    "a",
    "Fa",
    "Ga",
    "Xa",
    "G(p -> X q)",
    "G(p -> (q U r))",
    "G a",
    "F a",
    "a & X a",
    "G(a & X a)",
    "p U q",
    "F G a",
    "G F a",
    "X a",
    "G (p -> X p)",
    "(p U q) & G F r",
]


def run_case_in_subprocess(formula_str: str) -> dict:
    """Run decomp + pure reconstruct in an isolated fresh Python process."""
    child_code = f'''
import sys
import json
import traceback
from pathlib import Path

proj = Path(r"{PROJECT_ROOT}").resolve()
sys.path.insert(0, str(proj))

import spot
from kr import decompose_aut, reconstruct_ltl_1level_buchi

fs = {formula_str!r}
try:
    f = spot.formula(fs)
    aut = f.translate()
    casc = decompose_aut(aut)

    info = {{
        "formula": fs,
        "num_levels": casc.num_levels,
        "num_states": casc.num_states,
        "num_acc_configs": len(casc.accepting_configs()),
        "num_configs": len(casc.all_configs()),
    }}

    info["recovered"] = reconstruct_ltl_1level_buchi(casc)

    print("RESULT_JSON:" + json.dumps(info))
except Exception as e:
    info = {{"formula": fs}}
    info["error"] = str(e)[:200]
    info["tb"] = traceback.format_exc()[-300:]
    print("RESULT_JSON:" + json.dumps(info))
'''

    proc = subprocess.run(
        [sys.executable, "-c", child_code],
        capture_output=True,
        text=True,
        timeout=45,
        cwd=PROJECT_ROOT,
    )

    out = (proc.stdout or "") + (proc.stderr or "")
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("RESULT_JSON:"):
            return json.loads(line[len("RESULT_JSON:") :])

    rc = proc.returncode
    if rc == 139:
        return {"formula": formula_str, "error": "SEGV (exit 139) in subprocess", "rc": rc}
    return {
        "formula": formula_str,
        "error": "no RESULT_JSON marker",
        "stdout_head": out[:400],
        "rc": rc,
    }


def safe_equiv(orig_formula_str: str, ltl_str: str) -> str:
    """Check equivalence in isolated process."""
    if not ltl_str or ltl_str.startswith(("ERROR", "NOT_IMPLEMENTED", "PAPER_STYLE_TOO_LARGE")):
        return "N/A"

    code = f'''
import sys
from pathlib import Path
proj = Path(r"{PROJECT_ROOT}").resolve()
sys.path.insert(0, str(proj))
import spot
f = spot.formula({orig_formula_str!r})
orig_aut = f.translate("Buchi")
try:
    if {ltl_str!r} in ("true", "false"):
        other = spot.formula({ltl_str!r})
    else:
        other = spot.formula({ltl_str!r}).translate("Buchi")
    print("EQ:" + str(bool(spot.are_equivalent(orig_aut, other))))
except Exception as e:
    print("EQ:err:" + str(e)[:80])
'''
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=PROJECT_ROOT,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    for line in out.splitlines():
        if line.strip().startswith("EQ:"):
            return line.strip()[3:]
    return "err:no-output"


def main():
    print("=== kr pure paper reconstruction test (subproc isolated) ===")
    print("Using the algebraic path (reach formulas + fin_c + Muller assembly).")
    print(f"Project root: {PROJECT_ROOT}")
    print()

    results = []
    successes = []
    for fs in CASES:
        print(f"--- {fs} ---")
        res = run_case_in_subprocess(fs)
        results.append(res)

        if "error" in res:
            print(f"  ERROR: {res['error']}")
            continue

        print(
            f"  levels={res['num_levels']} states={res['num_states']} "
            f"configs={res.get('num_configs')} acc_configs={res.get('num_acc_configs')}"
        )

        rec = res.get("recovered", "")[:85]
        print(f"  recovered: {rec}{'...' if len(res.get('recovered','')) > 85 else ''}")

        eq = safe_equiv(fs, res["recovered"])
        print(f"  equiv to original? {eq}")
        if eq == "True":
            successes.append(fs)

    print()
    print("=== Summary ===")
    one_level = sum(1 for r in results if r.get("num_levels") == 1)
    multi = sum(1 for r in results if r.get("num_levels", 0) > 1)
    print(f"1-level cases: {one_level}")
    print(f"Multi-level cases: {multi}")
    print(f"Roundtripping formulas (pure paper path, EQUIV True): {successes}")
    print()
    print("All runs completed. Equiv False on complex cases is expected until")
    print("further polish of the 5 formulas (see algorithm.md + gaps in STATUS.md).")


if __name__ == "__main__":
    main()
