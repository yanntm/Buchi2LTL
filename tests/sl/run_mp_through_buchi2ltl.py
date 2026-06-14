#!/usr/bin/env python3
"""
testing/run_mp_through_buchi2ltl.py

Run the kr/ MP-class benchmark ladder through the buchi2ltl heuristic engine
(backward labeling + f2/tN SCC absorption heuristics) and report, per formula:
the technique used, whether the recovered formula is equivalent to the original
(the soundness gate — heuristics can over/under-approximate), and the output size
(DAG / unfolded tree / distinct temporals). This is a SIDE-BY-SIDE view of how the
heuristic path handles the same cases the kr/ cascade path does — no mixing, just
comparison.

Each formula in an isolated subprocess with a low timeout (the heuristic can fail,
loop, or segfault on some inputs — that IS the finding, bucketed not hidden).

Run from project root (prefer backgrounding it):
    python3 testing/run_mp_through_buchi2ltl.py
    python3 testing/run_mp_through_buchi2ltl.py "G(p -> (q U r))"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

PER = int(os.environ.get("B2L_TIMEOUT", "12"))

# Same ladder as kr/testing/survey_mp_cascade.py (kept in sync by hand).
CASES = [
    "true", "false", "a",
    "Ga", "G(a | b)", "G(a -> X b)", "a & X a", "G(a -> X a)", "G(a & X a)",
    "X a", "X X a", "X X X a", "X(a & X a)",
    "Fa", "a U b", "F(a & b)", "F(a & X b)", "a | X b",
    "Fa | Gb", "Ga | Gb", "Fa & Gb", "(a U b) | Gc", "Ga | Fb",
    "GFa", "G(a -> F b)", "G(a | F b)", "GFa & GFb", "GFa & GFb & GFc",
    "G(a -> F b) & G(c -> F d)",
    "G(p -> (q U r))",
    "FGa", "F(a & G b)", "FGa | FGb",
    "GFa -> GFb", "(GFa & FGb)",
]


def run_case(fs: str) -> dict:
    child = f'''
import sys, json, traceback, io, contextlib
from pathlib import Path
sys.path.insert(0, str(Path(r"{PROJECT_ROOT}").resolve()))
import spot
from aut2ltl.sl.reconstruction import reconstruct_ltl

def sizes(f):
    seen, kinds, st = set(), {{}}, [f]
    while st:
        g = st.pop(); i = g.id()
        if i in seen: continue
        seen.add(i); k = g.kindstr(); kinds[k] = kinds.get(k, 0) + 1
        for c in g: st.append(c)
    def _ts(g, memo):
        if g.id() in memo: return memo[g.id()]
        v = 1 + sum(_ts(c, memo) for c in g)
        memo[g.id()] = v; return v
    temp = sum(v for k, v in kinds.items() if k in ("U","M","R","W","F","G"))
    return [len(seen), _ts(f, {{}}), temp]

fs = {fs!r}
info = {{"formula": fs}}
try:
    aut = spot.formula(fs).translate("GeneralizedBuchi", "Small", "High")
    # buchi2ltl prints debug; swallow stdout so only our marker survives
    with contextlib.redirect_stdout(io.StringIO()):
        out = reconstruct_ltl(aut)
    rec = out[0] if isinstance(out, (tuple, list)) else out
    technique = out[2] if isinstance(out, (tuple, list)) and len(out) > 2 else "?"
    info["technique"] = str(technique)
    if rec is None:
        info["result"] = "NONE"
    else:
        recf = rec if isinstance(rec, spot.formula) else spot.formula(str(rec))
        info["size"] = sizes(recf)
        orig = spot.formula(fs).translate("Buchi")
        info["equiv"] = bool(spot.are_equivalent(orig, recf.translate("Buchi")))
        info["result"] = "OK"
except Exception as e:
    info["result"] = "ERROR"; info["error"] = str(e)[:140]
    info["tb"] = traceback.format_exc()[-200:]
print("RESULT_JSON:" + json.dumps(info))
'''
    try:
        proc = subprocess.run([sys.executable, "-c", child], capture_output=True,
                              text=True, timeout=PER, cwd=PROJECT_ROOT)
    except subprocess.TimeoutExpired:
        return {"formula": fs, "result": "TIMEOUT"}
    out = (proc.stdout or "") + (proc.stderr or "")
    for line in out.splitlines():
        if line.strip().startswith("RESULT_JSON:"):
            return json.loads(line.strip()[len("RESULT_JSON:"):])
    if proc.returncode == 139:
        return {"formula": fs, "result": "SEGV"}
    return {"formula": fs, "result": "ERROR", "error": "no marker"}


def main():
    cases = sys.argv[1:] or CASES
    print(f"=== kr MP ladder through buchi2ltl (subproc isolated, {PER}s/case) ===\n")
    print(f"  {'formula':22s} {'result':8s} {'technique':9s} {'equiv':6s} "
          f"{'DAG/tree/temp':18s}")
    print("  " + "-" * 74)
    n_ok = n_eq = n_bad = 0
    for fs in cases:
        r = run_case(fs)
        res = r.get("result", "?")
        s = r.get("size")
        ss = f"{s[0]}/{s[1]}/{s[2]}" if s else "-"
        eq = {True: "True", False: "FALSE"}.get(r.get("equiv"), "-")
        if res == "OK":
            n_ok += 1
            if r.get("equiv") is True: n_eq += 1
            elif r.get("equiv") is False: n_bad += 1
        tech = r.get("technique", "-") if res == "OK" else (r.get("error", "")[:30] if res == "ERROR" else "")
        print(f"  {fs:22s} {res:8s} {str(tech):9s} {eq:6s} {ss:18s}")
    print(f"\n=== {n_ok} produced output; {n_eq} equiv=True, {n_bad} equiv=FALSE "
          f"(of {len(cases)} cases) ===")


if __name__ == "__main__":
    main()
