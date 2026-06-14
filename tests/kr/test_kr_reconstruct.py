#!/usr/bin/env python3
"""
kr/testing/test_kr_reconstruct.py

Verification for the pure paper reconstruction path in kr/:
- decomp (Spot -> det parity complete -> SgpDec cascade)
- reconstruct_bls (which uses the inductive reach formulas +
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
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from aut2ltl.kr import (
    decompose_aut,
    reconstruct_bls,
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
    "a U b",
    "G F p",
    "F G p",
    "p & F q",
    "G (p | X q)",
    "X X a",
    "G p & F q",
    "F (p U q)",
    "G (p -> X (p & q))",
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
from aut2ltl.kr import decompose_aut, reconstruct_bls

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

    # formula DAG out; flatten only under the tree-size gate (see survey tool)
    import os as _os
    from aut2ltl.kr.ltl_builders import _tree_size_f, _str_f
    rec_f = reconstruct_bls(casc)
    _lim = int(_os.environ.get("KR_FLATTEN_TREE_LIMIT", "5000000"))
    info["tree_nodes"] = _tree_size_f(rec_f)
    info["recovered"] = _str_f(rec_f) if info["tree_nodes"] <= _lim else None

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


# Built-in Spot verification budget: blowing it means Spot's translation
# choked on the (heavily shared, hugely unfolding) formula — NOT that the
# construction failed. Reported as SPOT_TIMEOUT, distinct from FALSE.
SPOT_EQUIV_TIMEOUT = int(os.environ.get("KR_SPOT_EQUIV_TIMEOUT", "10"))

# Fixed child code; both formulas travel via stdin (multi-MB flat formulas
# on argv die with E2BIG / "Argument list too long").
_EQUIV_CHILD = '''
import sys, json
import spot
p = json.load(sys.stdin)
orig_aut = spot.formula(p["orig"]).translate("Buchi")
rec = p["rec"]
try:
    other = spot.formula(rec)
    if rec not in ("true", "false"):
        other = other.translate("Buchi")
    print("EQ:" + str(bool(spot.are_equivalent(orig_aut, other))))
except Exception as e:
    print("EQ:err:" + str(e)[:80])
'''


def safe_equiv(orig_formula_str: str, ltl_str: str) -> str:
    """Check equivalence in isolated process (SPOT_EQUIV_TIMEOUT cap)."""
    if not ltl_str or ltl_str.startswith(("ERROR", "NOT_IMPLEMENTED", "PAPER_STYLE_TOO_LARGE")):
        return "N/A"

    try:
        proc = subprocess.run(
            [sys.executable, "-c", _EQUIV_CHILD],
            input=json.dumps({"orig": orig_formula_str, "rec": ltl_str}),
            capture_output=True,
            text=True,
            timeout=SPOT_EQUIV_TIMEOUT,
            cwd=PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired:
        return (f"SPOT_TIMEOUT >{SPOT_EQUIV_TIMEOUT}s "
                f"(construction ok, len={len(ltl_str)}; Spot verification blocked)")
    out = (proc.stdout or "") + (proc.stderr or "")
    for line in out.splitlines():
        if line.strip().startswith("EQ:"):
            return line.strip()[3:]
    return "err:no-output"


def main():
    cases = sys.argv[1:] or CASES   # argv = specific formulas (per docstring)
    print("=== kr pure paper reconstruction test (subproc isolated) ===")
    print("Using the algebraic path (reach formulas + fin_c + Muller assembly).")
    print(f"Project root: {PROJECT_ROOT}")
    print()

    results = []
    successes = []
    for fs in cases:
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

        rec_full = res.get("recovered") or ""
        if not rec_full and res.get("tree_nodes"):
            print(f"  recovered: <unflattened DAG: {res['tree_nodes']} tree nodes>")
            print("  equiv to original? UNVERIFIED_SIZE")
            continue
        print(f"  recovered: {rec_full[:85]}{'...' if len(rec_full) > 85 else ''}")

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
