#!/usr/bin/env python3
"""
kr/testing/probe_dag_oracle.py

Cross-oracle the DAG-native buchi2ltl engine (buchi2ltl.reconstruction_dag) against
the legacy STRING engine (buchi2ltl.reconstruction): run BOTH on the same TGBA (no
scc_labeler) and check they agree:
  * both DECLINE (UNSUPPORTED), or
  * both produce formulas that are are_equivalent to each other AND to the original.

This is the faithfulness gate for the rewrite — once it is clean across the
corpus, the DAG engine can replace the string one. Per formula in an isolated
subprocess, 15s budget.

Run from project root:
    python3 kr/testing/probe_dag_oracle.py
    python3 kr/testing/probe_dag_oracle.py "G F a" "a U b"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

PER = int(os.environ.get("KR_ORACLE_TIMEOUT", "15"))

# The MP ladder (same as run_mp_through_buchi2ltl): a spread of sl-handled and
# sl-declined cases — both engines must agree on every one.
CASES = [
    "true", "false", "a",
    "Ga", "G(a | b)", "G(a -> X b)", "a & X a", "G(a -> X a)", "G(a & X a)",
    "X a", "X X a", "X X X a", "X(a & X a)",
    "Fa", "a U b", "F(a & b)", "F(a & X b)", "a | X b",
    "Fa | Gb", "Ga | Gb", "Fa & Gb", "(a U b) | Gc", "Ga | Fb",
    "GFa", "G(a -> F b)", "G(a | F b)", "GFa & GFb", "GFa & GFb & GFc",
    "G(p -> (q U r))",
    "FGa", "F(a & G b)", "FGa | FGb",
    "GFa -> GFb", "(GFa & FGb)",
]

_CHILD = r'''
import sys, json, contextlib, io
from pathlib import Path
sys.path.insert(0, str(Path(r"{root}").resolve()))
import spot
from buchi2ltl.reconstruction import reconstruct_ltl
from buchi2ltl.reconstruction_dag import reconstruct_ltl_dag

def tree(f):
    memo = {{}}
    def rec(g):
        i = g.id()
        if i in memo: return memo[i]
        v = 1 + sum(rec(c) for c in g); memo[i] = v; return v
    return rec(f)

def is_decl(x):
    return x is None or (isinstance(x, str) and "UNSUPPORTED" in x)

fs = {fs!r}
info = {{"formula": fs}}
try:
    aut = spot.formula(fs).translate("GeneralizedBuchi", "Small", "High")
    with contextlib.redirect_stdout(io.StringIO()):
        s = reconstruct_ltl(aut)[0]
        dg = reconstruct_ltl_dag(aut)[0]
    ds, dd = is_decl(s), is_decl(dg)
    if ds and dd:
        info["bucket"] = "DECL_BOTH"
    elif ds != dd:
        info["bucket"] = "DECL_MISMATCH"; info["s_decl"] = ds; info["d_decl"] = dd
    else:
        sf = s if isinstance(s, spot.formula) else spot.formula(str(s))
        df = dg if isinstance(dg, spot.formula) else spot.formula(str(dg))
        eq_sd = bool(spot.are_equivalent(sf, df))
        orig = spot.formula(fs).translate("Buchi")
        eq_or = bool(spot.are_equivalent(orig, df.translate("Buchi")))
        info["tree_s"] = tree(sf); info["tree_d"] = tree(df)
        if eq_sd and eq_or:
            info["bucket"] = "MATCH"
        else:
            info["bucket"] = "NONEQ"; info["eq_sd"] = eq_sd; info["eq_or"] = eq_or
            info["df"] = str(df)[:80]
except Exception as e:
    import traceback
    info["bucket"] = "ERROR"; info["error"] = str(e)[:100]
    info["tb"] = traceback.format_exc()[-200:]
print("RESULT_JSON:" + json.dumps(info))
'''


def run(fs):
    child = _CHILD.format(root=PROJECT_ROOT, fs=fs)
    try:
        p = subprocess.run([sys.executable, "-c", child], capture_output=True,
                           text=True, timeout=PER, cwd=PROJECT_ROOT)
    except subprocess.TimeoutExpired:
        return {"formula": fs, "bucket": "TIMEOUT"}
    out = (p.stdout or "") + (p.stderr or "")
    for line in out.splitlines():
        if line.strip().startswith("RESULT_JSON:"):
            return json.loads(line.strip()[len("RESULT_JSON:"):])
    if p.returncode == 139:
        return {"formula": fs, "bucket": "SEGV"}
    return {"formula": fs, "bucket": "ERROR", "error": out[-200:]}


def rand_cases(n, aps, tree, seed):
    import spot
    out, seen = [], set()
    for f in spot.randltl(aps, tree_size=tree, seed=seed, simplify=3):
        if f.is_tt() or f.is_ff():
            continue
        s = str(f)
        if s not in seen:
            seen.add(s); out.append(s)
        if len(out) >= n:
            break
    return out


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "--rand":
        n = int(argv[1]) if len(argv) > 1 else 80
        cases = rand_cases(n, int(os.environ.get("KR_ORACLE_APS", "3")),
                           int(os.environ.get("KR_ORACLE_TREE", "12")),
                           int(os.environ.get("KR_ORACLE_SEED", "1")))
    else:
        cases = argv or CASES
    print(f"=== DAG vs STRING cross-oracle ({PER}s/case) ===\n")
    from collections import Counter
    counts = Counter()
    bad = []
    for fs in cases:
        r = run(fs)
        b = r["bucket"]
        counts[b] += 1
        if b in ("DECL_MISMATCH", "NONEQ", "ERROR", "SEGV", "TIMEOUT"):
            bad.append(r)
        sz = ""
        if b == "MATCH":
            sz = f"  tree s/d={r.get('tree_s')}/{r.get('tree_d')}"
        flag = "  <<<" if b in ("DECL_MISMATCH", "NONEQ", "ERROR", "SEGV") else ""
        print(f"  {fs:24s} {b:14s}{sz}{flag}")
    print("\n=== summary ===")
    for b, n in counts.most_common():
        print(f"  {b:14s} {n}")
    fail = sum(counts[b] for b in ("DECL_MISMATCH", "NONEQ", "ERROR", "SEGV"))
    print(f"\n  {'CLEAN — DAG engine matches string engine' if not fail else str(fail)+' DIVERGENCE(S)'}")
    if bad:
        print("  problems:")
        for r in bad:
            print(f"    {r['formula']:24s} {r['bucket']}  {r.get('error') or r.get('df') or ''}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
