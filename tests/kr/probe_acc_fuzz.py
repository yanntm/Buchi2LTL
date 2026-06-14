#!/usr/bin/env python3
"""
kr/testing/probe_acc_fuzz.py

How often does the config-indexed Acc(c) dispatch actually GATE (fire) on random
LTL formulas, routed through the real decompose workflow? If it fires on only a
sliver, it is narrow pattern-matching (the original objection); if it fires
broadly, it is a real workflow component. This probe measures that rate.

Method: generate N random formulas with Spot's `randltl` (small: few APs,
bounded tree size). Each formula in an ISOLATED subprocess with a LOW timeout
(random formulas blow up — deep cascades, GAP, translation — a blown budget is a
finding, counted as TIMEOUT/ERROR not conflated with a verdict). Per formula we
run `reconstruct_decomposed` with a STUB reconstruct that, per piece, records
whether `reconstruct_acc(casc).ok` (Acc would fire there) and
returns ⊤ (we only care about the GATE, not the output — avoids building the
possibly-huge BLS form). "Fired" = Acc gated on ≥1 piece.

Outcome buckets: FIRED / NOFIRE / ERROR / TIMEOUT. The headline is FIRED / (FIRED
+ NOFIRE) — the gate rate over formulas the workflow could process.

Run from project root (prefer backgrounding it):
    KR_FUZZ_N=60 KR_FUZZ_APS=2 python3 kr/testing/probe_acc_fuzz.py
    python3 kr/testing/probe_acc_fuzz.py 123        # seed
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
TREE = int(os.environ.get("KR_FUZZ_TREE", "8"))
PER = int(os.environ.get("KR_FUZZ_TIMEOUT", "10"))     # hard subprocess cap / formula
GAP = int(os.environ.get("KR_FUZZ_GAP_TIMEOUT", "6"))  # GAP/decompose budget / piece
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
from pathlib import Path
sys.path.insert(0, str(Path(r"{PROJECT_ROOT}").resolve()))
import spot
from aut2ltl.portfolio.decompose_recombine import reconstruct_decomposed
from aut2ltl.kr.acc import reconstruct_acc
from aut2ltl.kr.ltl_builders import _tt

fs = {fs!r}
info = {{"formula": fs}}
try:
    aut = spot.formula(fs).translate()
    n_pieces = [0]; n_acc = [0]
    def stub(casc):
        n_pieces[0] += 1
        try:
            if reconstruct_acc(casc).ok:
                n_acc[0] += 1
        except Exception:
            pass
        return _tt()    # only the GATE matters; don't build the real form
    reconstruct_decomposed(aut, reconstruct=stub, timeout={GAP})
    info["pieces"] = n_pieces[0]
    info["acc_pieces"] = n_acc[0]
    info["fired"] = n_acc[0] > 0
except Exception as e:
    info["error"] = str(e)[:120]
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
            else:
                r["bucket"] = "FIRED" if r.get("fired") else "NOFIRE"
            return r
    if proc.returncode == 139:
        return {"formula": fs, "bucket": "ERROR", "error": "SEGV"}
    return {"formula": fs, "bucket": "ERROR", "error": "no marker"}


def main():
    print(f"=== Acc(c) gate-rate fuzz: N={N} aps={APS} tree={TREE} seed={SEED} "
          f"(per-formula {PER}s, gap {GAP}s) ===\n")
    buckets = {"FIRED": [], "NOFIRE": [], "ERROR": [], "TIMEOUT": []}
    formulas = gen_formulas()
    for i, fs in enumerate(formulas):
        r = run_case(fs)
        b = r["bucket"]
        buckets[b].append(r)
        tag = {"FIRED": "FIRE", "NOFIRE": "    ", "ERROR": " ERR", "TIMEOUT": " T/O"}[b]
        extra = ""
        if b == "FIRED":
            extra = f"  ({r['acc_pieces']}/{r['pieces']} pieces)"
        elif b == "ERROR":
            extra = f"  {r.get('error','')[:60]}"
        print(f"  [{i+1:3d}/{len(formulas)}] {tag}  {fs[:60]:60s}{extra}")

    nf, nn = len(buckets["FIRED"]), len(buckets["NOFIRE"])
    proc = nf + nn
    print("\n=== summary ===")
    for b in ("FIRED", "NOFIRE", "ERROR", "TIMEOUT"):
        print(f"  {b:8s} {len(buckets[b])}")
    if proc:
        print(f"\n  GATE RATE (FIRED / processed) = {nf}/{proc} = {nf/proc*100:.1f}%")
    print("\n  sample FIRED:")
    for r in buckets["FIRED"][:8]:
        print(f"    {r['formula']}")
    print("  sample NOFIRE:")
    for r in buckets["NOFIRE"][:8]:
        print(f"    {r['formula']}")


if __name__ == "__main__":
    main()
