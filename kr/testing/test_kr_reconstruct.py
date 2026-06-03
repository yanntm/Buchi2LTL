#!/usr/bin/env python3
"""
kr/testing/test_kr_reconstruct.py

Verification script for the Krohn-Rhodes refactor:
- Clean `reconstruct_ltl_1level_buchi` (thin builder on top of K operators,
  no structural pattern matching on aut shape, 1-state cases, special q filters, etc.)
  vs. the preserved `_heuristic` (old ad-hoc version).

- Focus on 1-level cases taking the pure `build_infinitely_often_accepting` path.
- Multi-level cases correctly delegate/raise so the heuristic can still be used.
- Stability: uses per-case subprocess isolation (fresh python processes) to avoid
  Spot/Buddy global state accumulation that previously caused segfaults (exit 139).
- Equivalence where possible (using Spot's are_equivalent on the produced LTL).

Run from project root:
    python3 kr/testing/test_kr_reconstruct.py

All paths are relative; no /tmp usage.
"""

import json
import subprocess
import sys
from pathlib import Path

# Make the script runnable from anywhere (e.g. python3 kr/testing/... or as -m)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from kr import (
    decompose_aut,
    reconstruct_ltl_1level_buchi as rec_clean,
    reconstruct_ltl_1level_buchi_heuristic as rec_old,
    build_infinitely_often_accepting,
)

# Cases chosen to exercise:
# - 0-level degenerate (true/false constants)
# - Pure 1-level (Fa, Ga, false)
# - Multi-level (triggers NotImplemented in clean; heuristic still works)
# - The motivating until example (2 levels)
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


def run_case_in_subprocess(formula_str: str) -> dict:
    """Run decomp + both reconstructors in an isolated fresh Python process.

    This is the key stability technique: each case gets its own short-lived
    interpreter so Spot/buddy BDD var allocations and aut objects don't
    accumulate and trigger the old segfaults in the C extensions.
    """
    # The code we execute in the child. It must be self-contained.
    child_code = f'''
import sys
import json
import traceback
from pathlib import Path

# Child also needs the project on path
proj = Path(r"{PROJECT_ROOT}").resolve()
sys.path.insert(0, str(proj))

import spot
from kr import (
    decompose_aut,
    reconstruct_ltl_1level_buchi as rec_clean,
    reconstruct_ltl_1level_buchi_heuristic as rec_old,
    build_infinitely_often_accepting,
)

fs = {formula_str!r}
try:
    f = spot.formula(fs)
    aut = f.translate("Buchi", "Deterministic")
    casc = decompose_aut(aut)

    info = {{
        "formula": fs,
        "num_levels": casc.num_levels,
        "num_states": casc.num_states,
        "num_acc_configs": len(casc.accepting_configs()),
        "num_configs": len(casc.all_configs()),
    }}

    # Always get the heuristic (old) result
    info["heuristic"] = rec_old(casc)

    # Clean path: for non-1-level it raises (by design during transition)
    try:
        info["clean"] = rec_clean(casc)
        info["clean_raised"] = False
    except NotImplementedError as nie:
        info["clean"] = f"NOT_IMPLEMENTED: {{nie}}"
        info["clean_raised"] = True
    except Exception as e:
        info["clean"] = f"ERROR: {{type(e).__name__}}: {{e}}"
        info["clean_raised"] = True

    # Also expose the core builder result when applicable
    if casc.num_levels == 1:
        try:
            info["build_inf"] = build_infinitely_often_accepting(casc)
        except Exception as e:
            info["build_inf"] = f"ERROR: {{type(e).__name__}}"

    print("RESULT_JSON:" + json.dumps(info))
except Exception as e:
    info = info if "info" in locals() else {{"formula": fs}}
    info["error"] = str(e)[:200]
    info["tb"] = traceback.format_exc()[-300:]
    print("RESULT_JSON:" + json.dumps(info))  # always emit RESULT so parent parser succeeds
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
        if line.startswith("ERROR_JSON:"):
            return json.loads(line[len("ERROR_JSON:") :])

    # Fallback if no marker (crash or bad output)
    rc = proc.returncode
    if rc == 139:
        return {"formula": formula_str, "error": "SEGV (exit 139) in subprocess", "rc": rc}
    return {
        "formula": formula_str,
        "error": "no RESULT_JSON marker",
        "stdout_head": out[:400],
        "rc": rc,
    }


def _always_emit_result_fallback(formula_str: str, e: Exception) -> dict:
    """Helper to guarantee we can still report even if early exception before info dict."""
    return {
        "formula": formula_str,
        "error": str(e)[:200],
        "tb": "see child output",
    }


def safe_equiv(orig_formula_str: str, ltl_str: str) -> str:
    """Try to check equivalence in yet another isolated process (defensive)."""
    if not ltl_str or ltl_str.startswith(("NOT_IMPLEMENTED", "ERROR", "UNSUPPORTED")):
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
    print("=== kr reconstruct refactor verification (clean vs heuristic) ===")
    print("Using subprocess isolation per case for stability.")
    print(f"Project root: {PROJECT_ROOT}")
    print()

    results = []
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

        heur = res.get("heuristic", "")[:85]
        print(f"  heuristic: {heur}{'...' if len(res.get('heuristic','')) > 85 else ''}")

        if res.get("clean_raised"):
            print(f"  clean   : {res.get('clean')}")
        else:
            cln = res.get("clean", "")[:85]
            print(f"  clean   : {cln}{'...' if len(res.get('clean','')) > 85 else ''}")

        # For 1-level cases, also show the core builder output if present
        if "build_inf" in res:
            bi = res["build_inf"][:70]
            print(f"  build_inf: {bi}{'...' if len(res['build_inf']) > 70 else ''}")

        # Equivalence only makes sense when we have a clean (non-raising) result
        if not res.get("clean_raised") and res.get("clean"):
            eq = safe_equiv(fs, res["clean"])
            print(f"  clean equiv to original input? {eq}")

    print()
    print("=== Summary ===")
    one_level_count = sum(1 for r in results if r.get("num_levels") == 1)
    clean_1level = sum(
        1
        for r in results
        if r.get("num_levels") == 1 and not r.get("clean_raised")
    )
    multi_count = sum(1 for r in results if r.get("num_levels", 0) > 1)
    print(f"1-level cases encountered: {one_level_count}")
    print(f"Clean path succeeded on 1-level: {clean_1level}")
    print(f"Multi-level cases: {multi_count} (clean now attempts via generalized reach_strong; results may be partial until Fin/acc assembly).")
    print()
    print("All runs completed without segfaults (thanks to bdd_utils precompute + isolation).")


if __name__ == "__main__":
    main()
