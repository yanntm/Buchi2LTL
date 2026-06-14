#!/usr/bin/env python3
"""
kr/testing/probe_gate_redet.py

Question (2026-06-14): if we DETERMINIZE a HOA (as `_to_split_form` does:
postprocess deterministic+generic, then sat_minimize) and then ask Spot for a
TGBA again ("Small","High") — do we get back a "clean" TGBA that buchi2ltl can
label, or is determinization a one-way loss the gate can't recover from?

The gate (`try_heuristic_gate`) already does `postprocess(aut,"TGBA","Small",
"High")` internally before running buchi2ltl. So this probe compares, per case,
buchi2ltl run on the TGBA derived from the RAW translate form vs from the
DETERMINIZED form, plus the structural facts (states / deterministic? / SCCs /
acceptance) of each, to see whether the re-postprocess recovers a labelable
form.

Per case, isolated subprocess, 15s. Run from project root:
    python3 kr/testing/probe_gate_redet.py
    python3 kr/testing/probe_gate_redet.py "F G a | F G b"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

PER = int(os.environ.get("KR_PROBE_TIMEOUT", "15"))

CASES = [
    "FGa | FGb",        # the documented hard case (det coBüchi defeats the gate)
    "Fa | Gb",          # OR-decomposable; gate wins whole
    "Ga | Fb",
    "GFa & GFb",        # AND case
    "F(a & X b)",       # gate declines whole -> cascade buchi
    "G(a -> F b)",
]

_CHILD = r'''
import sys, json, contextlib, io
from pathlib import Path
sys.path.insert(0, str(Path(r"{root}").resolve()))
import spot
from aut2ltl.sl.reconstruction import reconstruct_ltl

def tree(f):
    memo = {{}}
    def rec(g):
        i = g.id()
        if i in memo: return memo[i]
        v = 1 + sum(rec(c) for c in g); memo[i] = v; return v
    return rec(f)

def facts(a):
    return {{"states": a.num_states(),
             "det": bool(a.is_deterministic()),
             "sccs": spot.scc_info(a).scc_count(),
             "acc": str(a.get_acceptance())[:40]}}

def run_bl(a):
    with contextlib.redirect_stdout(io.StringIO()):
        r = reconstruct_ltl(a)
    f = r.formula
    if f is None or (isinstance(f, str) and "UNSUPPORTED" in f):
        return {{"decl": True}}
    return {{"decl": False, "tree": tree(f)}}

fs = {fs!r}
info = {{"formula": fs}}
try:
    raw = spot.formula(fs).translate()
    det = spot.postprocess(raw, "deterministic", "generic")
    if det.num_states() <= 30:
        m = spot.sat_minimize(det)
        if m is not None and m.num_states() < det.num_states():
            det = m
    tgba_raw = spot.postprocess(raw, "TGBA", "Small", "High")
    tgba_det = spot.postprocess(det, "TGBA", "Small", "High")
    info["raw"] = facts(raw)
    info["det"] = facts(det)
    info["tgba_from_raw"] = facts(tgba_raw)
    info["tgba_from_det"] = facts(tgba_det)
    info["bl_from_raw"] = run_bl(tgba_raw)
    info["bl_from_det"] = run_bl(tgba_det)
except Exception as e:
    import traceback
    info["error"] = str(e)[:120]; info["tb"] = traceback.format_exc()[-200:]
print("RESULT_JSON:" + json.dumps(info))
'''


def run(fs):
    child = _CHILD.format(root=PROJECT_ROOT, fs=fs)
    try:
        p = subprocess.run([sys.executable, "-c", child], capture_output=True,
                           text=True, timeout=PER, cwd=PROJECT_ROOT)
    except subprocess.TimeoutExpired:
        return {"formula": fs, "error": "TIMEOUT"}
    out = (p.stdout or "") + (p.stderr or "")
    for line in out.splitlines():
        if line.strip().startswith("RESULT_JSON:"):
            return json.loads(line.strip()[len("RESULT_JSON:"):])
    return {"formula": fs, "error": out[-200:]}


def _f(d):
    return f"st={d['states']} det={'Y' if d['det'] else 'N'} sccs={d['sccs']} acc={d['acc']}"


def _bl(d):
    return "DECLINE" if d.get("decl") else f"ok(tree={d.get('tree')})"


def main():
    cases = sys.argv[1:] or CASES
    print(f"=== determinize then re-postprocess: does buchi2ltl recover? ({PER}s) ===\n")
    for fs in cases:
        r = run(fs)
        print(f"--- {fs} ---")
        if "error" in r:
            print(f"    ERROR: {r['error']}"); continue
        print(f"    raw           : {_f(r['raw'])}")
        print(f"    det(gen+sat)  : {_f(r['det'])}")
        print(f"    TGBA<-raw     : {_f(r['tgba_from_raw'])}   buchi2ltl: {_bl(r['bl_from_raw'])}")
        print(f"    TGBA<-det     : {_f(r['tgba_from_det'])}   buchi2ltl: {_bl(r['bl_from_det'])}")


if __name__ == "__main__":
    main()
