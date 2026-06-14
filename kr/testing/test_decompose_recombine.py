#!/usr/bin/env python3
"""kr/testing/test_decompose_recombine.py — front-end wrapper test.

Exercises kr.decompose_recombine.reconstruct_decomposed end-to-end on the
acceptance-driven census cases (AND by acceptance set, OR by strength) plus
fall-through cases. Per-case subprocess isolation; small Spot budget; a blown
budget is a finding (reported, never waited on).

    python3 kr/testing/test_decompose_recombine.py
    python3 kr/testing/test_decompose_recombine.py "GFa & GFb" "Ga | Fb"
"""
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

EQUIV_TIMEOUT = int(os.environ.get("KR_SPOT_EQUIV_TIMEOUT", "10"))

# (formula, expected split kind). 'and' = generalized-Büchi conjunctive
# recurrence; 'or' = mixed strength / disjunction; 'none' = single piece.
CASES = [
    ("GFa & GFb", "and"),
    ("GFa & GFb & GFc", "and"),
    ("Ga | Fb", "or"),
    ("(a U b) | Gc", "or"),
    ("GFa & FGb", "and"),   # reactivity: Inf(0) & Fin(1) (Rabin-pair conjunct)
    ("GFa & Gb", "none"),   # safety folds into one acc set
    ("FGa | FGb", "none"),  # persistence union folds into one co-Büchi strength
    ("a U b", "none"),
]

CHILD = '''
import sys, json
from pathlib import Path
sys.path.insert(0, r"{root}")
import spot
from kr.decompose_recombine import reconstruct_decomposed, split_report
from kr.ltl_builders import _tree_size_f

def dag_nodes(f):
    seen, stack = set(), [f]
    while stack:
        g = stack.pop()
        if g.id() in seen: continue
        seen.add(g.id()); stack.extend(g)
    return len(seen)

def temporals(f):
    seen, stack, n = set(), [f], 0
    while stack:
        g = stack.pop()
        if g.id() in seen: continue
        seen.add(g.id())
        if g.kindstr() in ("U","M","R","W","F","G"): n += 1
        stack.extend(g)
    return n

import os as _os
fs = {fs!r}
# kr input contract is an AUTOMATON (HOA). The LTL string is only the test's
# convenient way to name a case; we translate to an automaton and feed THAT.
aut = spot.formula(fs).translate()
kind, npieces = split_report(aut)
rec = reconstruct_decomposed(aut).formula
ntree = _tree_size_f(rec)
# Flatten only under the gate: huge fall-through cases (e.g. FGa|FGb at 2^60)
# must not str()-explode. Over the gate -> UNVERIFIED_SIZE.
_lim = int(_os.environ.get("KR_FLATTEN_TREE_LIMIT", "5000000"))
print("RESULT_JSON:" + json.dumps({{
    "formula": fs, "kind": kind, "npieces": npieces,
    "dag": dag_nodes(rec), "temporals": temporals(rec),
    "tree": ntree, "rec": str(rec) if ntree <= _lim else None,
}}))
'''

_EQUIV_CHILD = '''
import sys, json, spot
p = json.load(sys.stdin)
try:
    A = spot.formula(p["orig"]).translate("Buchi")
    B = spot.formula(p["rec"])
    if p["rec"] not in ("true","false"): B = B.translate("Buchi")
    print("EQ:" + str(bool(spot.are_equivalent(A, B))))
except Exception as e:
    msg = str(e)
    tag = "ACC_CAP" if "acceptance" in msg.lower() or "mark" in msg.lower() else "EXC"
    print("EQ:" + tag + ":" + msg[:80])
'''


def run(fs):
    proc = subprocess.run([sys.executable, "-c", CHILD.format(root=str(PROJECT_ROOT), fs=fs)],
                          capture_output=True, text=True, timeout=40, cwd=PROJECT_ROOT)
    out = (proc.stdout or "") + (proc.stderr or "")
    for line in out.splitlines():
        if line.strip().startswith("RESULT_JSON:"):
            return json.loads(line.strip()[len("RESULT_JSON:"):])
    return {"formula": fs, "error": out[-300:]}


def equiv(orig, rec):
    try:
        proc = subprocess.run([sys.executable, "-c", _EQUIV_CHILD],
                              input=json.dumps({"orig": orig, "rec": rec}),
                              capture_output=True, text=True,
                              timeout=EQUIV_TIMEOUT, cwd=PROJECT_ROOT)
    except subprocess.TimeoutExpired:
        return f"SPOT_TIMEOUT>{EQUIV_TIMEOUT}s"
    out = (proc.stdout or "") + (proc.stderr or "")
    for line in out.splitlines():
        if line.strip().startswith("EQ:"):
            return line.strip()[3:]
    return "err"


def main():
    cases = [(a, None) for a in sys.argv[1:]] or CASES
    print("=== decompose-and-recombine front end ===")
    n_true = n_kind_ok = 0
    for fs, want in cases:
        res = run(fs)
        if "error" in res:
            print(f"--- {fs}: ERROR {res['error'][:120]}")
            continue
        kind_tag = res["kind"]
        if want is not None:
            ok = "OK" if kind_tag == want else f"MISMATCH(want {want})"
            n_kind_ok += int(kind_tag == want)
        else:
            ok = ""
        if res["rec"] is None:
            eq = f"UNVERIFIED_SIZE({res['tree']} tree nodes)"
        else:
            eq = equiv(fs, res["rec"])
        n_true += int(eq == "True")
        print(f"--- {fs}")
        print(f"    split={kind_tag}({res['npieces']}) {ok}  "
              f"DAG={res['dag']} temporals={res['temporals']} tree={res['tree']}")
        print(f"    equiv? {eq}")
    print()
    print(f"Summary: equiv True = {n_true}/{len(cases)}"
          + (f"; split-kind OK = {n_kind_ok}" if any(w for _, w in cases) else ""))


if __name__ == "__main__":
    main()
