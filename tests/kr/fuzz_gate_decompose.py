#!/usr/bin/env python3
"""
kr/testing/fuzz_gate_decompose.py

Soundness + adopt-rate fuzz for the buchi2ltl heuristic gate wired into the
decompose dispatcher (kr/heuristic_gate.py + kr/decompose_recombine.py), over a
LARGE random LTL corpus — the "try the bigger set" audit.

The production gate adopts buchi2ltl's output WITHOUT an equivalence check,
trusting it to be sound-by-construction (it self-validates its f2/t2 fragments
and returns UNSUPPORTED rather than a wrong formula). This fuzz AUDITS that
claim at scale by running with KR_GATE_VERIFY=1: the gate then re-checks every
adopted candidate against its node automaton (BOUNDED — small automaton, tiny
candidate) and counts `rejected`. The headline is total `rejected` across the
corpus: it MUST be 0 for the no-check production path to be sound. A nonzero
count names a formula where buchi2ltl is unsound (and the check saved us).

Also reported: adopt rate (how often the gate fires on a real random workload),
and a secondary end-to-end are_equivalent(orig, output) confirmation wherever
the output is small enough to translate under the cap (gate-adopted outputs
always are; kr-only giants bucket as UNVERIFIED, as in the MP survey).

Each formula in an ISOLATED subprocess with a hard per-formula cap (random
formulas blow up; a blown budget is a finding, bucketed not hidden).

Run from project root (prefer backgrounding it; log under kr/testing/logs/):
    KR_FUZZ_N=60 KR_FUZZ_APS=2 python3 kr/testing/fuzz_gate_decompose.py
    python3 kr/testing/fuzz_gate_decompose.py 123        # seed
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

N = int(os.environ.get("KR_FUZZ_N", "60"))
APS = int(os.environ.get("KR_FUZZ_APS", "2"))
TREE = int(os.environ.get("KR_FUZZ_TREE", "10"))
PER = int(os.environ.get("KR_FUZZ_TIMEOUT", "15"))      # hard subprocess cap / formula
GAP = int(os.environ.get("KR_FUZZ_GAP_TIMEOUT", "8"))   # GAP/decompose budget / piece
EQ_TREE_CAP = int(os.environ.get("KR_FUZZ_EQ_CAP", "200000"))
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("KR_FUZZ_SEED", "1"))


def gen_formulas() -> list:
    """N distinct, non-constant random LTL formula strings via randltl."""
    import spot
    out, seen = [], set()
    g = spot.randltl(APS, tree_size=TREE, seed=SEED, simplify=3)
    for f in g:
        if f.is_tt() or f.is_ff():
            continue
        s = str(f)
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= N:
            break
    return out


def run_case(fs: str) -> dict:
    child = f'''
import os, sys, json, traceback
os.environ["KR_GATE_VERIFY"] = "1"     # AUDIT: gate re-checks every adopted piece
from pathlib import Path
sys.path.insert(0, str(Path(r"{PROJECT_ROOT}").resolve()))
import spot
from aut2ltl.portfolio.decompose_recombine import reconstruct_decomposed
from aut2ltl.portfolio.heuristic_gate import gate_stats, reset_gate_stats

def tree_size(f):
    memo = {{}}
    def rec(g):
        i = g.id()
        if i in memo: return memo[i]
        v = 1 + sum(rec(c) for c in g); memo[i] = v; return v
    return rec(f)

fs = {fs!r}
info = {{"formula": fs}}
try:
    aut = spot.formula(fs).translate()
    reset_gate_stats()
    rec = reconstruct_decomposed(aut, timeout={GAP}).formula
    info["stats"] = gate_stats()
    ts = tree_size(rec)
    info["tree"] = ts
    if ts <= {EQ_TREE_CAP}:
        orig = spot.formula(fs).translate("Buchi")
        info["equiv"] = bool(spot.are_equivalent(orig, rec.translate("Buchi")))
    else:
        info["equiv"] = None     # UNVERIFIED by size (kr-only giant)
except Exception as e:
    info["error"] = str(e)[:120]
    info["tb"] = traceback.format_exc()[-200:]
print("RESULT_JSON:" + json.dumps(info))
'''
    try:
        proc = subprocess.run([sys.executable, "-c", child], capture_output=True,
                              text=True, timeout=PER, cwd=PROJECT_ROOT)
    except subprocess.TimeoutExpired:
        return {"formula": fs, "bucket": "TIMEOUT"}
    out = (proc.stdout or "") + (proc.stderr or "")
    for line in out.splitlines():
        if line.strip().startswith("RESULT_JSON:"):
            r = json.loads(line.strip()[len("RESULT_JSON:"):])
            if "error" in r:
                r["bucket"] = "ERROR"
            elif r.get("equiv") is True:
                r["bucket"] = "EQUIV"
            elif r.get("equiv") is False:
                r["bucket"] = "FALSE"
            else:
                r["bucket"] = "UNVERIF"
            return r
    if proc.returncode == 139:
        return {"formula": fs, "bucket": "ERROR", "error": "SEGV"}
    return {"formula": fs, "bucket": "ERROR", "error": "no marker", "tb": out[-200:]}


def main():
    print(f"=== gate soundness/adopt fuzz: N={N} aps={APS} tree={TREE} seed={SEED} "
          f"(per-formula {PER}s, gap {GAP}s, VERIFY=1) ===\n")
    buckets = {"EQUIV": [], "FALSE": [], "UNVERIF": [], "ERROR": [], "TIMEOUT": []}
    tot_tried = tot_adopt = tot_rej = 0
    formulas = gen_formulas()
    for i, fs in enumerate(formulas):
        r = run_case(fs)
        b = r["bucket"]
        buckets[b].append(r)
        st = r.get("stats", {})
        tot_tried += st.get("tried", 0)
        tot_adopt += st.get("adopted", 0)
        tot_rej += st.get("rejected", 0)
        tag = {"EQUIV": "  ok", "FALSE": "FALSE", "UNVERIF": "unv ",
               "ERROR": " err", "TIMEOUT": " t/o"}[b]
        ad = st.get("adopted", 0)
        rj = st.get("rejected", 0)
        flag = "  <<< UNSOUND" if (b == "FALSE" or rj) else ""
        extra = f"  adopt={ad} rej={rj}" if r.get("stats") else f"  {r.get('error','')[:40]}"
        print(f"  [{i+1:3d}/{len(formulas)}] {tag}  {fs[:54]:54s}{extra}{flag}")

    print("\n=== summary ===")
    for b in ("EQUIV", "FALSE", "UNVERIF", "ERROR", "TIMEOUT"):
        print(f"  {b:8s} {len(buckets[b])}")
    print(f"\n  gate: tried={tot_tried} adopted={tot_adopt} "
          f"rejected={tot_rej}  (adopt rate "
          f"{tot_adopt}/{tot_tried}={(tot_adopt/tot_tried*100 if tot_tried else 0):.0f}%)")
    print(f"\n  SOUNDNESS: equiv=FALSE={len(buckets['FALSE'])}, "
          f"gate rejections={tot_rej}  "
          f"(both MUST be 0 for the no-check production path)")
    if buckets["FALSE"]:
        print("  !!! equiv=FALSE formulas:")
        for r in buckets["FALSE"]:
            print(f"      {r['formula']}")
    sys.exit(1 if (buckets["FALSE"] or tot_rej) else 0)


if __name__ == "__main__":
    main()
