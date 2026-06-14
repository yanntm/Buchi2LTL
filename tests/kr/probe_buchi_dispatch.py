#!/usr/bin/env python3
"""
kr/testing/probe_buchi_dispatch.py

Probe the direct Büchi dispatch (kr/acceptance_dispatch.reconstruct_buchi)
against the Muller-DNF path (reconstruct_bls): for each case report whether the
cascade is detected Büchi, the size A/B (DAG / tree / distinct temporals), and
— the soundness gate — whether the dispatch formula is equivalent to the
ORIGINAL automaton.

Per case in an isolated subprocess with a 15s budget (a blown budget is the
finding). Run from project root:
    python3 kr/testing/probe_buchi_dispatch.py
    python3 kr/testing/probe_buchi_dispatch.py "G(p -> (q U r))"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

BUDGET = int(os.environ.get("KR_PROBE_TIMEOUT", "15"))

# Büchi (recurrence) cases + a few non-Büchi controls (dispatch must decline).
CASES = [
    "GFa", "G(a -> F b)", "G(a | F b)", "G(p -> (q U r))",   # Büchi
    "Fa", "a U b", "FGa", "Ga",                              # controls (not Büchi)
]


def run_case(fs: str) -> dict:
    child = f'''
import os, sys, json, traceback
from pathlib import Path
sys.path.insert(0, str(Path(r"{PROJECT_ROOT}").resolve()))
import spot
from aut2ltl.kr import decompose_aut, reconstruct_bls
from aut2ltl.kr.acceptance_dispatch import is_buchi_cascade, reconstruct_buchi
from aut2ltl.kr.ltl_builders import _tree_size_f

def sizes(f):
    seen, kinds, st = set(), {{}}, [f]
    while st:
        g = st.pop(); i = g.id()
        if i in seen: continue
        seen.add(i); k = g.kindstr(); kinds[k] = kinds.get(k, 0) + 1
        for c in g: st.append(c)
    temp = sum(v for k, v in kinds.items() if k in ("U","M","R","W","F","G"))
    return [len(seen), _tree_size_f(f), temp]

fs = {fs!r}
info = {{"formula": fs}}
try:
    aut = spot.formula(fs).translate()
    casc = decompose_aut(aut)
    info["is_buchi"] = bool(is_buchi_cascade(casc))
    info["acc"] = str(casc.original_aut.get_acceptance())
    bf = reconstruct_buchi(casc)
    info["dispatched"] = bf is not None
    if bf is not None:
        info["buchi_size"] = sizes(bf)
        # Muller baseline: the dispatch is now WIRED as a pre-check in
        # reconstruct_ltl_paper_style, so reconstruct_bls would itself dispatch;
        # force the pure Muller form for the A/B with KR_DISPATCH_BUCHI=0.
        os.environ["KR_DISPATCH_BUCHI"] = "0"
        info["muller_size"] = sizes(reconstruct_bls(casc))
        os.environ.pop("KR_DISPATCH_BUCHI", None)
        orig = spot.formula(fs).translate("Buchi")
        info["equiv_orig"] = bool(spot.are_equivalent(orig, bf.translate("Buchi")))
except Exception as e:
    info["error"] = str(e)[:160]
    info["tb"] = traceback.format_exc()[-200:]
print("RESULT_JSON:" + json.dumps(info))
'''
    try:
        proc = subprocess.run([sys.executable, "-c", child], capture_output=True,
                              text=True, timeout=BUDGET, cwd=PROJECT_ROOT)
    except subprocess.TimeoutExpired:
        return {"formula": fs, "error": f"TIMEOUT >{BUDGET}s"}
    out = (proc.stdout or "") + (proc.stderr or "")
    for line in out.splitlines():
        if line.strip().startswith("RESULT_JSON:"):
            return json.loads(line.strip()[len("RESULT_JSON:"):])
    if proc.returncode == 139:
        return {"formula": fs, "error": "SEGV (rc 139)"}
    return {"formula": fs, "error": "no marker", "head": out[:200]}


def main():
    cases = sys.argv[1:] or CASES
    print("=== Büchi dispatch probe (subproc isolated, "
          f"{BUDGET}s/case) ===\n")
    print(f"  {'formula':18s} {'büchi?':6s} {'disp':5s} {'equiv':6s} "
          f"{'büchi DAG/tree/temp':22s} {'muller DAG/tree/temp':22s}")
    print("  " + "-" * 92)
    for fs in cases:
        r = run_case(fs)
        if "error" in r:
            print(f"  {fs:18s} ERROR: {r['error']}")
            continue
        b = r.get("buchi_size")
        m = r.get("muller_size")
        bs = f"{b[0]}/{b[1]}/{b[2]}" if b else "-"
        ms = f"{m[0]}/{m[1]}/{m[2]}" if m else "-"
        eq = {True: "True", False: "FALSE"}.get(r.get("equiv_orig"), "-")
        print(f"  {fs:18s} {str(r.get('is_buchi')):6s} "
              f"{str(r.get('dispatched')):5s} {eq:6s} {bs:22s} {ms:22s}")
        if r.get("equiv_orig") is False:
            print(f"      !!! NOT EQUIVALENT TO ORIGINAL — acc={r.get('acc')}")


if __name__ == "__main__":
    main()
