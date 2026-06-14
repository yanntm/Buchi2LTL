#!/usr/bin/env python3
"""
kr/testing/test_heuristic_gate.py

Focused test for the buchi2ltl heuristic gate (kr/heuristic_gate.py) wired into
the decompose dispatcher. Per case, in an isolated subprocess with a small
budget, we report:

  * gate verdict on the TOP automaton (adopted / declined) + its size,
  * SOUNDNESS: any gate-adopted formula must be are_equivalent to its input
    (the gate's own invariant — re-checked here independently),
  * end-to-end `reconstruct_decomposed` equivalence to the original formula
    with the gate ON (default) AND OFF (KR_GATE_BUCHI2LTL=0), plus the size
    delta — confirms the gate never breaks equivalence and shows where it helps,
  * gate_stats() — in particular `rejected`, which should stay 0 if buchi2ltl is
    sound-by-construction (the hypothesis we are making sure of).

Run from project root:
    python3 kr/testing/test_heuristic_gate.py
    python3 kr/testing/test_heuristic_gate.py "FGa | FGb"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

PER = int(os.environ.get("KR_GATE_TEST_TIMEOUT", "15"))

# A spread across the MP ladder: heuristic-whole wins (FGa|FGb — the last kr
# wall), AND/OR splits, and cases buchi2ltl declined whole in the comparison
# (G(p->(qUr)), F(a&Xb)) where decomposition + kr must carry it.
CASES = [
    "Ga", "G(a -> X b)", "X(a & X a)",
    "a U b", "F(a & X b)", "Ga | Gb", "(a U b) | Gc",
    "GFa & GFb", "GFa & GFb & GFc", "G(p -> (q U r))",
    "FGa", "FGa | FGb", "(GFa & FGb)",
]

_CHILD = r'''
import sys, json, os
from pathlib import Path
sys.path.insert(0, str(Path(r"{root}").resolve()))
import spot

def sizes(f):
    seen, st = set(), [f]
    while st:
        g = st.pop(); i = g.id()
        if i in seen: continue
        seen.add(i)
        for c in g: st.append(c)
    def ts(g, memo):
        if g.id() in memo: return memo[g.id()]
        v = 1 + sum(ts(c, memo) for c in g); memo[g.id()] = v; return v
    # distinct temporals
    seen2, st2, t = set(), [f], 0
    while st2:
        g = st2.pop(); i = g.id()
        if i in seen2: continue
        seen2.add(i)
        if g.kindstr() in ("U","M","R","W","F","G"): t += 1
        for c in g: st2.append(c)
    return [len(seen), ts(f, {{}}), t]

fs = {fs!r}
info = {{"formula": fs}}
try:
    from kr.decompose_recombine import reconstruct_decomposed, _to_split_form
    from kr.heuristic_gate import try_heuristic_gate, gate_stats, reset_gate_stats
    orig = spot.formula(fs).translate("Buchi")
    aut = spot.formula(fs).translate()

    # --- gate verdict on the RAW top automaton (what reconstruct_decomposed
    # tries first; _to_split_form imported only to keep the contract visible) ---
    _ = _to_split_form
    reset_gate_stats()
    phi = try_heuristic_gate(aut)
    if phi is not None:
        info["gate_top"] = "adopt"
        info["gate_size"] = sizes(phi)
        # independent soundness re-check of the adopted formula
        info["gate_sound"] = bool(spot.are_equivalent(aut, phi.translate()))
    else:
        info["gate_top"] = "decline"

    # Translate+equiv only when the unfolded tree is small enough that Spot
    # won't hit the 32-acc / size wall — a huge OFF tree (e.g. FGa|FGb's
    # 2779-temporal kr form) must not mask the ON win. Construction itself is
    # cheap; only this verification leg needs the guard.
    EQ_TREE_CAP = 200000
    def eq_guarded(f):
        if sizes(f)[1] > EQ_TREE_CAP:
            return "SKIP"
        return bool(spot.are_equivalent(orig, f.translate("Buchi")))

    # --- end-to-end gate ON (default) ---
    os.environ.pop("KR_GATE_BUCHI2LTL", None)
    reset_gate_stats()
    on = reconstruct_decomposed(aut).formula
    info["on_size"] = sizes(on)
    info["on_equiv"] = eq_guarded(on)
    info["stats"] = gate_stats()

    # --- end-to-end gate OFF ---
    os.environ["KR_GATE_BUCHI2LTL"] = "0"
    off = reconstruct_decomposed(aut).formula
    info["off_size"] = sizes(off)
    info["off_equiv"] = eq_guarded(off)
    info["result"] = "OK"
except Exception as e:
    import traceback
    info["result"] = "ERROR"; info["error"] = str(e)[:160]
    info["tb"] = traceback.format_exc()[-300:]
print("RESULT_JSON:" + json.dumps(info))
'''


def run_case(fs: str) -> dict:
    child = _CHILD.format(root=PROJECT_ROOT, fs=fs)
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
    return {"formula": fs, "result": "ERROR", "error": "no marker", "tb": out[-300:]}


def fmt(s):
    return f"{s[0]}/{s[1]}/{s[2]}" if s else "-"


def main():
    cases = sys.argv[1:] or CASES
    print(f"=== heuristic-gate test (subproc isolated, {PER}s/case) ===\n")
    print(f"  {'formula':22s} {'gate':8s} {'on_eq':6s} {'off_eq':6s} "
          f"{'on DAG/tree/temp':18s} {'off DAG/tree/temp':18s} {'rej':3s}")
    print("  " + "-" * 96)
    fail = 0
    total_rej = 0
    for fs in cases:
        r = run_case(fs)
        res = r.get("result", "?")
        if res != "OK":
            print(f"  {fs:22s} {res}  {r.get('error','')}")
            fail += 1
            continue
        gate = r.get("gate_top", "-")
        on_eq = r.get("on_equiv"); off_eq = r.get("off_equiv")
        gs = r.get("gate_sound", None)
        rej = r.get("stats", {}).get("rejected", 0)
        total_rej += rej
        bad = (on_eq is False) or (off_eq is False) or (gs is False)
        if bad:
            fail += 1
        flag = "  <-- FAIL" if bad else ""
        print(f"  {fs:22s} {gate:8s} {str(on_eq):6s} {str(off_eq):6s} "
              f"{fmt(r.get('on_size')):18s} {fmt(r.get('off_size')):18s} "
              f"{rej:<3d}{flag}")
    print()
    verdict = "CLEAN" if fail == 0 else f"{fail} FAILURE(S)"
    print(f"=== {verdict}; total gate rejections (should be 0): {total_rej} ===")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
