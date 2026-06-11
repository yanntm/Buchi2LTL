#!/usr/bin/env python3
"""
kr/testing/survey_mp_cascade.py

Survey tool for P0 test-case selection: classify small formulas by
Manna-Pnueli class (spot.mp_class), decompose each to its cascade, and
report cascade depth (levels + per-level sizes) and current pure-paper
roundtrip status (Spot equiv).

Goal: find the smallest 2-level cascades per MP class (weakest first:
safety -> guarantee -> obligation -> recurrence -> persistence ->
reactivity) to drive targeted R4/Rws0 work.

Subprocess isolation per formula (Spot/buddy stability). Run from root:

    python3 kr/testing/survey_mp_cascade.py            # full survey
    python3 kr/testing/survey_mp_cascade.py "Fa" "Ga"  # specific
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Small candidates spanning the Manna-Pnueli hierarchy. Kept tiny (1-2 APs,
# small automata) so cascades stay tractable and failures are debuggable.
CANDIDATES = [
    # bottom / safety
    "true", "false", "a",
    "Ga", "G(a | b)", "G(a -> X b)", "a & X a", "G(a -> X a)", "G(a & X a)",
    "X a", "X X a",
    # guarantee (co-safety)
    "Fa", "a U b", "F(a & b)", "F(a & X b)", "a | X b",
    # obligation (boolean comb. of safety+guarantee)
    "Fa | Gb", "Ga | Gb", "Fa & Gb", "(a U b) | Gc",
    "Ga | Fb",
    # recurrence (Buchi / Pi2)
    "GFa", "G(a -> F b)", "G(a | F b)", "GFa & GFb",
    # persistence (coBuchi / Sigma2)
    "FGa", "F(a & G b)", "FGa | FGb",
    # reactivity
    "GFa -> GFb", "(GFa & FGb)",
]


def survey_one(formula_str: str, timeout: int = 45) -> dict:
    """Classify + decompose + reconstruct + equiv in a fresh process."""
    child_code = f'''
import sys, json, traceback
from pathlib import Path
proj = Path(r"{PROJECT_ROOT}").resolve()
sys.path.insert(0, str(proj))
import spot
from kr import decompose_aut, reconstruct_ltl_1level_buchi

fs = {formula_str!r}
info = {{"formula": fs}}
try:
    f = spot.formula(fs)
    info["mp"] = spot.mp_class(f)            # B/S/G/O/R/P/T
    info["mp_v"] = spot.mp_class(f, "v")     # verbose name
    aut = f.translate()
    casc = decompose_aut(aut)
    info["levels"] = casc.num_levels
    info["level_sizes"] = [lv.size for lv in casc.levels]
    info["states"] = casc.num_states
    info["configs"] = len(casc.all_configs())
    rec = reconstruct_ltl_1level_buchi(casc)
    info["recovered"] = rec
    if rec and not rec.startswith(("ERROR", "NOT_IMPLEMENTED", "PAPER_STYLE_TOO_LARGE")):
        orig_aut = f.translate("Buchi")
        other = spot.formula(rec)
        other_aut = other if rec in ("true", "false") else other.translate("Buchi")
        if rec in ("true", "false"):
            info["equiv"] = bool(spot.are_equivalent(orig_aut, spot.formula(rec)))
        else:
            info["equiv"] = bool(spot.are_equivalent(orig_aut, other_aut))
    else:
        info["equiv"] = None
except Exception as e:
    info["error"] = str(e)[:200]
    info["tb"] = traceback.format_exc()[-300:]
print("RESULT_JSON:" + json.dumps(info))
'''
    try:
        proc = subprocess.run(
            [sys.executable, "-c", child_code],
            capture_output=True, text=True, timeout=timeout, cwd=PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired:
        return {"formula": formula_str, "error": f"TIMEOUT >{timeout}s"}
    out = (proc.stdout or "") + (proc.stderr or "")
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("RESULT_JSON:"):
            return json.loads(line[len("RESULT_JSON:"):])
    if proc.returncode == 139:
        return {"formula": formula_str, "error": "SEGV (rc 139)"}
    return {"formula": formula_str, "error": "no marker", "head": out[:300]}


# Weakest-first display order for mp_class letters.
MP_ORDER = {"B": 0, "S": 1, "G": 2, "O": 3, "R": 4, "P": 5, "T": 6}
MP_NAME = {"B": "bottom", "S": "safety", "G": "guarantee", "O": "obligation",
           "R": "recurrence", "P": "persistence", "T": "reactivity"}


def main():
    args = sys.argv[1:]
    cases = args if args else CANDIDATES
    print("=== MP-class x cascade-depth survey (subproc isolated) ===")
    print(f"{len(cases)} formulas\n")

    results = []
    for fs in cases:
        res = survey_one(fs)
        results.append(res)
        if "error" in res:
            print(f"  {fs:24s}  ERROR: {res['error']}")
        else:
            eq = res.get("equiv")
            eqs = {True: "True ", False: "FALSE", None: "n/a  "}[eq]
            rec = (res.get("recovered") or "")[:48]
            print(f"  {fs:24s}  mp={res['mp']}({MP_NAME.get(res['mp'],'?'):11s}) "
                  f"L={res['levels']} sizes={res['level_sizes']} "
                  f"equiv={eqs} rec={rec}")

    # Group by MP class, weakest first; highlight 2L cases.
    print("\n=== By MP class (weakest first) — 2-level cases marked ** ===")
    ok = [r for r in results if "error" not in r]
    ok.sort(key=lambda r: (MP_ORDER.get(r["mp"], 9), r["levels"], r["states"]))
    cur = None
    for r in ok:
        if r["mp"] != cur:
            cur = r["mp"]
            print(f"\n-- {MP_NAME.get(cur, cur)} ({cur}) --")
        mark = "**" if r["levels"] == 2 else "  "
        eq = {True: "equiv=True", False: "equiv=FALSE", None: "equiv=n/a"}[r.get("equiv")]
        print(f" {mark} L={r['levels']} sizes={r['level_sizes']} {eq:12s} {r['formula']}")

    two_l = [r for r in ok if r["levels"] == 2]
    two_l_fail = [r for r in two_l if r.get("equiv") is False]
    print(f"\n=== Summary: {len(two_l)} two-level cases, "
          f"{len(two_l_fail)} of them failing equiv ===")
    for r in two_l_fail:
        print(f"  CANDIDATE TARGET: {r['formula']} "
              f"(mp={MP_NAME.get(r['mp'])}, sizes={r['level_sizes']})")


if __name__ == "__main__":
    main()
