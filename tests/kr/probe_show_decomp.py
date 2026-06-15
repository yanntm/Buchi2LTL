#!/usr/bin/env python3
"""
kr/testing/probe_show_decomp.py

For each case, print the reconstructed formula (flattened) + technique + temporal
count under BOTH gate-orderings:
  * KR_GATE_UNDER_DECOMP=0 — OLD: gate first (short-circuits decomposition);
  * KR_GATE_UNDER_DECOMP=1 — NEW: decompose first, gate the leaves.

So we can read exactly what the AND/OR split produces vs the gate-whole form on
the cases whose size changed. Per case+mode, isolated subprocess, 15s.

Run from project root:
    python3 kr/testing/probe_show_decomp.py
    python3 kr/testing/probe_show_decomp.py "GFa & GFb"
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PER = int(os.environ.get("KR_PROBE_TIMEOUT", "15"))

CASES = ["GFa & GFb", "GFa & GFb & GFc", "(GFa & FGb)", "(a U b) | Gc",
         "Fa | Gb"]  # last = an OR win, for contrast

_CHILD = r'''
import sys, contextlib, io
from pathlib import Path
sys.path.insert(0, str(Path(r"{root}").resolve()))
import spot
from aut2ltl.portfolio.decompose_recombine import reconstruct_decomposed
from aut2ltl.ltl.builders import _str_f, _tree_size_f

def temporals(f):
    seen, st, t = set(), [f], 0
    while st:
        g = st.pop(); i = g.id()
        if i in seen: continue
        seen.add(i)
        if g.kindstr() in ("U","M","R","W","F","G"): t += 1
        for c in g: st.append(c)
    return t

fs = {fs!r}
with contextlib.redirect_stdout(io.StringIO()):
    r = reconstruct_decomposed(spot.formula(fs).translate())
print("TECH:" + r.technique_str())
print("TEMP:" + str(temporals(r.formula)))
print("TREE:" + str(_tree_size_f(r.formula)))
print("FORM:" + _str_f(r.formula))
'''


def run(fs, under):
    child = _CHILD.format(root=PROJECT_ROOT, fs=fs)
    env = dict(os.environ, KR_GATE_UNDER_DECOMP=under)
    try:
        p = subprocess.run([sys.executable, "-c", child], capture_output=True,
                           text=True, timeout=PER, cwd=PROJECT_ROOT, env=env)
    except subprocess.TimeoutExpired:
        return {"err": "TIMEOUT"}
    d = {}
    for line in ((p.stdout or "") + (p.stderr or "")).splitlines():
        for k in ("TECH", "TEMP", "TREE", "FORM"):
            if line.startswith(k + ":"):
                d[k.lower()] = line[len(k) + 1:]
    return d or {"err": (p.stdout + p.stderr)[-200:]}


def main():
    cases = sys.argv[1:] or CASES
    for fs in cases:
        print(f"\n=== {fs} ===")
        for mode, name in (("0", "OLD gate-first    "), ("1", "NEW decompose-first")):
            d = run(fs, mode)
            if "err" in d:
                print(f"  {name}: ERROR {d['err']}"); continue
            print(f"  {name}: tech={d.get('tech','?'):14s} "
                  f"temporal={d.get('temp','?')} tree={d.get('tree','?')}")
            print(f"      {d.get('form','?')}")


if __name__ == "__main__":
    main()
