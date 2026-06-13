#!/usr/bin/env python3
"""
kr/testing/survey_sizes.py

Size census across the MP-class ladder, measured on the GOTO path:
`reconstruct_decomposed(aut)` (the decompose-and-recombine front end), NOT the
monolithic `reconstruct_ltl_paper_style` that `measure_formula_dag.py` calls.
That distinction matters — the survey/default pipeline routes through the
decompose entry, so this is the size profile of what we actually ship.

Per case (subprocess isolated, fresh Python — Spot/buddy state accumulation
can segv): split kind, cascade levels/sizes, DAG unique nodes, unfolded tree
nodes, distinct temporal binaries (U/M/R/W/F/G — the 32-acc-cap driver),
tree/DAG sharing factor, and construction wall time (decomposition included).

Construction-only; no Spot equiv (see survey_mp_cascade.py for verdicts). A
blown construction budget (KR_CONSTRUCT_TIMEOUT, default 30s) is reported, not
waited on.

Run from project root:
    python3 kr/testing/survey_sizes.py
    python3 kr/testing/survey_sizes.py "a U b" "G(a -> X b)"   # specific
    KR_SIZE_PATH=monolithic python3 kr/testing/survey_sizes.py  # A/B vs reconstruct_bls
    KR_FOLD_FIN_REACH=0 python3 kr/testing/survey_sizes.py      # Fin fold off, A/B

Mirrors survey_mp_cascade.py's case list and isolation discipline.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

CONSTRUCT_TIMEOUT = int(os.environ.get("KR_CONSTRUCT_TIMEOUT", "30"))

# Same ladder as survey_mp_cascade.py (kept in sync by hand).
CANDIDATES = [
    "true", "false", "a",
    "Ga", "G(a | b)", "G(a -> X b)", "a & X a", "G(a -> X a)", "G(a & X a)",
    "X a", "X X a", "X X X a", "X(a & X a)",
    "Fa", "a U b", "F(a & b)", "F(a & X b)", "a | X b",
    "Fa | Gb", "Ga | Gb", "Fa & Gb", "(a U b) | Gc", "Ga | Fb",
    "GFa", "G(a -> F b)", "G(a | F b)", "GFa & GFb", "GFa & GFb & GFc",
    "G(a -> F b) & G(c -> F d)",
    "FGa", "F(a & G b)", "FGa | FGb",
    "GFa -> GFb", "(GFa & FGb)",
]


def measure_one(formula_str: str, timeout: int = CONSTRUCT_TIMEOUT) -> dict:
    """Build via the decompose entry in a fresh process; return size metrics."""
    child_code = f'''
import sys, json, time, traceback, os as _os
from pathlib import Path
proj = Path(r"{PROJECT_ROOT}").resolve()
sys.path.insert(0, str(proj))
import spot
from kr import decompose_aut, reconstruct_bls
from kr.decompose_recombine import reconstruct_decomposed, split_report
from kr.ltl_builders import _tree_size_f

# Default path is the GOTO decompose entry; KR_SIZE_PATH=monolithic switches
# to per-cascade reconstruct_bls for A/B.
PATH = _os.environ.get("KR_SIZE_PATH", "decompose")

def dag_unique_and_kinds(f):
    seen, kinds = set(), {{}}
    stack = [f]
    while stack:
        g = stack.pop()
        gid = g.id()
        if gid in seen:
            continue
        seen.add(gid)
        k = g.kindstr()
        kinds[k] = kinds.get(k, 0) + 1
        for child in g:
            stack.append(child)
    return len(seen), kinds

fs = {formula_str!r}
info = {{"formula": fs, "path": PATH}}
try:
    f = spot.formula(fs)
    info["mp"] = spot.mp_class(f)
    aut = f.translate()
    casc = decompose_aut(aut)
    info["levels"] = casc.num_levels
    info["level_sizes"] = [lv.size for lv in casc.levels]
    info["configs"] = len(casc.all_configs())
    kind, npieces = split_report(aut)
    info["split"] = f"{{kind}}({{npieces}})"

    t0 = time.monotonic()
    rec_f = reconstruct_bls(casc) if PATH == "monolithic" else reconstruct_decomposed(aut)
    info["build_s"] = round(time.monotonic() - t0, 3)

    n_unique, kinds = dag_unique_and_kinds(rec_f)
    info["dag_nodes"] = n_unique
    info["tree_nodes"] = _tree_size_f(rec_f)
    info["temporal"] = sum(v for k, v in kinds.items() if k in ("U","M","R","W","F","G"))
    info["sharing"] = round(info["tree_nodes"] / max(n_unique, 1), 1)
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
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("RESULT_JSON:"):
            return json.loads(line[len("RESULT_JSON:"):])
    if proc.returncode == 139:
        return {"formula": formula_str, "error": "SEGV (rc 139)"}
    return {"formula": formula_str, "error": "no marker", "head": out[:300]}


MP_ORDER = {"B": 0, "S": 1, "G": 2, "O": 3, "R": 4, "P": 5, "T": 6}
MP_NAME = {"B": "bottom", "S": "safety", "G": "guarantee", "O": "obligation",
           "R": "recurrence", "P": "persistence", "T": "reactivity"}


def main():
    args = sys.argv[1:]
    cases = args if args else CANDIDATES
    path = os.environ.get("KR_SIZE_PATH", "decompose")
    fold = os.environ.get("KR_FOLD_FIN_REACH", "1") != "0"
    print("=== kr size census (subproc isolated) ===")
    print(f"path={path}  fin_reach_fold={'on' if fold else 'off'}  "
          f"{len(cases)} formulas  (construction-only; budget {CONSTRUCT_TIMEOUT}s)\n")

    hdr = (f"  {'formula':24s} {'mp':3s} {'split':9s} {'L':>2s} "
           f"{'DAG':>8s} {'tree':>14s} {'temp':>5s} {'shar':>8s} {'build':>7s}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    results = []
    for fs in cases:
        res = measure_one(fs)
        results.append(res)
        if "error" in res:
            print(f"  {fs:24s} ERROR: {res['error']}")
            continue
        print(f"  {fs:24s} {res['mp']:3s} {res.get('split','?'):9s} "
              f"{res['levels']:>2d} {res['dag_nodes']:>8d} {res['tree_nodes']:>14d} "
              f"{res['temporal']:>5d} {str(res['sharing'])+'x':>8s} "
              f"{str(res['build_s'])+'s':>7s}")

    ok = [r for r in results if "error" not in r]
    ok.sort(key=lambda r: (MP_ORDER.get(r["mp"], 9), r["levels"], r["dag_nodes"]))
    print("\n=== By MP class (weakest first) ===")
    cur = None
    for r in ok:
        if r["mp"] != cur:
            cur = r["mp"]
            print(f"\n-- {MP_NAME.get(cur, cur)} ({cur}) --")
        print(f"  {r['formula']:24s} split={r.get('split','?'):9s} "
              f"DAG={r['dag_nodes']:>7d} tree={r['tree_nodes']:>14d} "
              f"temporal={r['temporal']:>4d}")

    if ok:
        tot_dag = sum(r["dag_nodes"] for r in ok)
        tot_temp = sum(r["temporal"] for r in ok)
        print(f"\n=== Totals over {len(ok)} built cases: "
              f"DAG nodes={tot_dag}, distinct temporals={tot_temp} ===")


if __name__ == "__main__":
    main()
