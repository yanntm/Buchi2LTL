#!/usr/bin/env python3
"""
kr/testing/probe_sl_soundness.py

CRITICAL soundness audit. The committed gate (kr/heuristic_gate.py) adopts
buchi2ltl output WITHOUT an equivalence check, on the belief that sl is
sound-by-construction (decline-or-correct). But old_results/*.csv contain
`equivalent=no` rows with `technique=sl` and a real recovered formula — i.e.
historically sl returned WRONG formulas, not declines. This probe checks whether
the CURRENT buchi2ltl still mistranslates those same originals.

For every distinct `equivalent=no` original across old_results/*.csv, run the
current `reconstruct_ltl` (translate -> reconstruct) in an isolated subprocess
and bucket:
  STILL_WRONG : returns a formula NOT are_equivalent to the original  (UNSOUND)
  NOW_OK      : returns an equivalent formula                         (fixed)
  DECLINES    : returns UNSUPPORTED / None                            (safe)
  ERROR/TIMEOUT

Headline: STILL_WRONG. If > 0, the gate MUST keep KR_GATE_VERIFY on (the bounded
per-piece equiv check) — dropping it is unsound. If 0, the old rows are stale and
the no-check gate is justified on this corpus.

Run from project root:
    python3 kr/testing/probe_sl_soundness.py
    KR_SND_MAX=120 python3 kr/testing/probe_sl_soundness.py
"""

import csv
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

PER = int(os.environ.get("KR_SND_TIMEOUT", "15"))
MAX = int(os.environ.get("KR_SND_MAX", "200"))


def collect() -> list:
    seen, out = set(), []
    for fp in sorted(glob.glob(str(PROJECT_ROOT / "old_results" / "*.csv"))):
        try:
            with open(fp) as f:
                for r in csv.DictReader(f):
                    if r.get("equivalent") == "no":
                        o = (r.get("original") or "").strip()
                        if o and o not in seen:
                            seen.add(o)
                            out.append(o)
        except Exception:
            pass
        if len(out) >= MAX:
            break
    return out[:MAX]


_CHILD = r'''
import sys, json, contextlib, io
from pathlib import Path
sys.path.insert(0, str(Path(r"{root}").resolve()))
import spot
from buchi2ltl.reconstruction import reconstruct_ltl

fs = {fs!r}
info = {{"formula": fs}}
try:
    aut = spot.formula(fs).translate("GeneralizedBuchi", "Small", "High")
    with contextlib.redirect_stdout(io.StringIO()):
        out = reconstruct_ltl(aut)
    rec = out.formula
    if rec is None or (isinstance(rec, str) and "UNSUPPORTED" in rec):
        info["bucket"] = "DECLINES"
    else:
        recf = rec if isinstance(rec, spot.formula) else spot.formula(str(rec))
        orig = spot.formula(fs).translate("Buchi")
        eq = bool(spot.are_equivalent(orig, recf.translate("Buchi")))
        info["bucket"] = "NOW_OK" if eq else "STILL_WRONG"
        if not eq:
            info["rec"] = str(recf)[:90]
except Exception as e:
    info["bucket"] = "ERROR"; info["error"] = str(e)[:80]
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
    return {"formula": fs, "bucket": "ERROR", "error": "no marker"}


def main():
    forms = collect()
    print(f"=== sl soundness audit: {len(forms)} distinct historical "
          f"equivalent=no originals, current engine, {PER}s/case ===\n")
    buckets = {"STILL_WRONG": [], "NOW_OK": [], "DECLINES": [], "ERROR": [], "TIMEOUT": []}
    for i, fs in enumerate(forms):
        r = run(fs)
        buckets[r["bucket"]].append(r)
        if r["bucket"] == "STILL_WRONG":
            print(f"  [{i+1:3d}] STILL_WRONG  {fs[:48]:50s} -> {r.get('rec','')[:50]}")
    print("\n=== summary ===")
    for b in ("STILL_WRONG", "NOW_OK", "DECLINES", "ERROR", "TIMEOUT"):
        print(f"  {b:12s} {len(buckets[b])}")
    nw = len(buckets["STILL_WRONG"])
    print(f"\n  VERDICT: {'UNSOUND — current sl still mistranslates ' + str(nw) + ' case(s); gate MUST keep KR_GATE_VERIFY' if nw else 'current sl mistranslates 0 of the historical failures (stale; no-check gate justified on this corpus)'}")
    sys.exit(1 if nw else 0)


if __name__ == "__main__":
    main()
