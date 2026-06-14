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
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Phase budgets (separate, so a slow case tells us WHICH phase blocked):
# construction (GAP decompose + formula build) vs Spot equiv verification.
# Spot translation chokes on our heavily-shared formulas (the flat unfolding
# has 100+ distinct temporal subformulas -> >32 acceptance sets); a blown
# equiv budget is reported as equiv=SPOT_TIMEOUT, NOT as a case failure.
CONSTRUCT_TIMEOUT = int(os.environ.get("KR_CONSTRUCT_TIMEOUT", "30"))
SPOT_EQUIV_TIMEOUT = int(os.environ.get("KR_SPOT_EQUIV_TIMEOUT", "10"))

# Fixed child for the equiv phase; formulas travel via stdin (a 5MB flat
# formula on argv dies with E2BIG, and embedding it in code is as bad).
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
    print("EQ:err:" + str(e)[:90])
'''


def spot_equiv(orig: str, rec: str):
    """True/False, or "SPOT_TIMEOUT" / "err:..." (verification blocked —
    distinct from a semantic FALSE; the construction already succeeded)."""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _EQUIV_CHILD],
            input=json.dumps({"orig": orig, "rec": rec}),
            capture_output=True, text=True,
            timeout=SPOT_EQUIV_TIMEOUT, cwd=PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired:
        return "SPOT_TIMEOUT"
    for line in (proc.stdout or "").splitlines():
        if line.startswith("EQ:"):
            payload = line[3:]
            # ONLY exact True/False are verdicts; an error payload must stay
            # an error (a previous version collapsed "err:Too many acceptance
            # sets" into boolean False — a phantom semantic failure).
            if payload == "True":
                return True
            if payload == "False":
                return False
            return payload  # "err:..." — verification blocked, not a verdict
    errtxt = (proc.stderr or proc.stdout or "no output").strip()
    first = next((l.strip() for l in errtxt.splitlines() if l.strip()), "no output")
    return "err:" + first[:100]

# Small candidates spanning the Manna-Pnueli hierarchy. Kept tiny (1-2 APs,
# small automata) so cascades stay tractable and failures are debuggable.
CANDIDATES = [
    # bottom / safety
    "true", "false", "a",
    "Ga", "G(a | b)", "G(a -> X b)", "a & X a", "G(a -> X a)", "G(a & X a)",
    # depth ladder: each X adds a cascade level (Xa=3L, XXa=4L, XXXa=5L) —
    # simple cases probing deep cascades now that the 3L dev guard is gone
    "X a", "X X a", "X X X a", "X(a & X a)",
    # guarantee (co-safety)
    "Fa", "a U b", "F(a & b)", "F(a & X b)", "a | X b",
    # obligation (boolean comb. of safety+guarantee)
    "Fa | Gb", "Ga | Gb", "Fa & Gb", "(a U b) | Gc",
    "Ga | Fb",
    # recurrence (Buchi / Pi2) — conjunctive recurrence AND-splits by acc set
    "GFa", "G(a -> F b)", "G(a | F b)", "GFa & GFb", "GFa & GFb & GFc",
    "G(a -> F b) & G(c -> F d)",
    "G(p -> (q U r))",   # the challenge case (reach-driven, none(1)); track regularly
                         # NB spaces in "q U r" — "qUr" parses as one atomic prop
    # persistence (coBuchi / Sigma2)
    "FGa", "F(a & G b)", "FGa | FGb",
    # reactivity — (GFa & FGb) is a Rabin-pair conjunct Inf&Fin that AND-splits
    "GFa -> GFb", "(GFa & FGb)",
]


def survey_one(formula_str: str, timeout: int = CONSTRUCT_TIMEOUT) -> dict:
    """Classify + decompose + reconstruct in a fresh process (construction
    phase only); the Spot equiv check runs in a SECOND subprocess with its
    own SPOT_EQUIV_TIMEOUT so blocked-verification is distinguishable from
    blocked-construction."""
    child_code = f'''
import sys, json, traceback, os as _os
from pathlib import Path
proj = Path(r"{PROJECT_ROOT}").resolve()
sys.path.insert(0, str(proj))
import spot
from kr import decompose_aut, reconstruct_bls
from kr.decompose_recombine import reconstruct_decomposed

# The decompose-and-recombine front end is the GOTO path (KR_DECOMPOSE=1,
# default); KR_DECOMPOSE=0 restores the monolithic path for A/B regression.
USE_DECOMP = _os.environ.get("KR_DECOMPOSE", "1") == "1"

fs = {formula_str!r}
info = {{"formula": fs}}
try:
    f = spot.formula(fs)
    info["mp"] = spot.mp_class(f)            # B/S/G/O/R/P/T
    info["mp_v"] = spot.mp_class(f, "v")     # verbose name
    aut = f.translate()
    casc = decompose_aut(aut)                # cascade info (input structure)
    info["levels"] = casc.num_levels
    info["level_sizes"] = [lv.size for lv in casc.levels]
    info["states"] = casc.num_states
    info["configs"] = len(casc.all_configs())
    # reconstruct returns the hash-consed formula DAG; flatten ONLY under the
    # tree-size gate (the flat string is the double-exp artifact — an oversized
    # case reports its DAG/tree sizes instead and equiv shows UNVERIFIED_SIZE).
    from kr.ltl_builders import _tree_size_f, _str_f
    if USE_DECOMP:
        _rr = reconstruct_decomposed(aut)
        rec_f = _rr.formula
        info["technique"] = _rr.technique_str()
    else:
        rec_f = reconstruct_bls(casc)
        info["technique"] = "bls"
    # 5M tree nodes ~ 40MB string: above every case Spot equiv has ever
    # completed, below the 64M+ monsters whose str() alone blows the budget.
    _lim = int(_os.environ.get("KR_FLATTEN_TREE_LIMIT", "5000000"))
    info["tree_nodes"] = _tree_size_f(rec_f)
    if info["tree_nodes"] <= _lim:
        info["recovered"] = _str_f(rec_f)
    else:
        info["recovered"] = None
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
        return {"formula": formula_str, "error": f"CONSTRUCT_TIMEOUT >{timeout}s"}
    out = (proc.stdout or "") + (proc.stderr or "")
    res = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("RESULT_JSON:"):
            res = json.loads(line[len("RESULT_JSON:"):])
            break
    if res is None:
        if proc.returncode == 139:
            return {"formula": formula_str, "error": "SEGV (rc 139)"}
        return {"formula": formula_str, "error": "no marker", "head": out[:300]}

    rec = res.get("recovered")
    if "error" not in res and rec and not rec.startswith(("ERROR", "NOT_IMPLEMENTED")):
        res["equiv"] = spot_equiv(formula_str, rec)
    elif "error" not in res and rec is None and res.get("tree_nodes"):
        # construction succeeded; flat form gated off by KR_FLATTEN_TREE_LIMIT
        res["equiv"] = f"UNVERIFIED_SIZE({res['tree_nodes']} tree nodes)"
    else:
        res["equiv"] = None
    return res


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
            eqs = {True: "True ", False: "FALSE", None: "n/a  "}.get(eq, str(eq)[:18])
            rec = (res.get("recovered") or "")[:48]
            print(f"  {fs:24s}  mp={res['mp']}({MP_NAME.get(res['mp'],'?'):11s}) "
                  f"L={res['levels']} sizes={res['level_sizes']} "
                  f"tech={res.get('technique','-'):16s} "
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
        eq = {True: "equiv=True", False: "equiv=FALSE",
              None: "equiv=n/a"}.get(r.get("equiv"), f"equiv={r.get('equiv')}")
        print(f" {mark} L={r['levels']} sizes={r['level_sizes']} {eq:12s} "
              f"tech={r.get('technique','-'):14s} {r['formula']}")

    two_l = [r for r in ok if r["levels"] == 2]
    two_l_fail = [r for r in two_l if r.get("equiv") is False]
    print(f"\n=== Summary: {len(two_l)} two-level cases, "
          f"{len(two_l_fail)} of them failing equiv ===")
    for r in two_l_fail:
        print(f"  CANDIDATE TARGET: {r['formula']} "
              f"(mp={MP_NAME.get(r['mp'])}, sizes={r['level_sizes']})")


if __name__ == "__main__":
    main()
