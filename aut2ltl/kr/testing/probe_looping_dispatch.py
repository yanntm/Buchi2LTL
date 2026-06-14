#!/usr/bin/env python3
"""
kr/testing/probe_looping_dispatch.py

Follow-up to probe_weak_dispatch.py: the GENERAL weak form (⋁_G end_in(G)) was a
size regression vs the wired Büchi/coBüchi dispatch (it enumerates an accepting
SCC's whole config-set H with a reach_to per config). This probe tests the
DEDICATED looping forms, which skip the H disjunction entirely (§9.3):

  looping-Büchi  (safety,    Π₁):  φ := ⋀_{C ∈ S_sink_rej}  ¬reach_to(ι, C)
  looping-coBüchi(guarantee,  Σ₁):  φ := ⋁_{C ∈ S_sink_acc}   reach_to(ι, C)

S_sink = configs mapping to an ABSORBING (trap) STATE of D — π⁻¹(sink), NOT
config-absorbing configs (on a multi-level cascade the sink state is covered by
configs that keep moving at deeper levels, so config-absorbing finds nothing).
Rejecting trap state for safety ("never reach it"), accepting trap state for
guarantee ("eventually reach it"). reach_to(ι,C) = reach_strong(ι,C,⊥,C,⊤). A
state s is a trap iff every out-edge self-loops (s→s); accepting/rejecting per
D's own acceptance on the self-loop marks.

The question: do these beat the current Büchi/coBüchi census on the safety /
guarantee walls (G(a->Xa), G(a->Xb), F(a&Xb))? Built directly on the single-piece
cascade (these walls are split=none). BUILD/EQUIV budgeted separately.

Per case in an isolated subprocess with a budget. Run from project root
(prefer backgrounding it):
    python3 kr/testing/probe_looping_dispatch.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

BUDGET = int(os.environ.get("KR_PROBE_TIMEOUT", "15"))

# (formula, expected class): safety -> ⋀¬reach_to, guarantee -> ⋁reach_to.
CASES = [
    ("Ga", "safety"), ("G(a | b)", "safety"), ("G(a -> X b)", "safety"),
    ("Ga | Gb", "safety"), ("G(a -> X a)", "safety"),
    ("Fa", "guarantee"), ("a U b", "guarantee"), ("F(a & b)", "guarantee"),
    ("F(a & X b)", "guarantee"),
]


def run_case(fs: str, cls: str) -> dict:
    child = f'''
import os, sys, json, traceback
from pathlib import Path
sys.path.insert(0, str(Path(r"{PROJECT_ROOT}").resolve()))
import spot
from aut2ltl.kr import decompose_aut
from aut2ltl.portfolio.decompose_recombine import _to_split_form
from aut2ltl.kr.config_graph import build_pruned_config_aut, reachable_configs
from aut2ltl.kr.reachability_operators import reach_strong
from aut2ltl.kr.ltl_builders import _And, _Or, _Not, _tt, _ff, _simp_f, _tree_size_f

def sizes(f):
    seen, kinds, st = set(), {{}}, [f]
    while st:
        g = st.pop(); i = g.id()
        if i in seen: continue
        seen.add(i); k = g.kindstr(); kinds[k] = kinds.get(k, 0) + 1
        for c in g: st.append(c)
    temp = sum(v for k, v in kinds.items() if k in ("U","M","R","W","F","G"))
    return [len(seen), _tree_size_f(f), temp]

def init_config(casc):
    if casc.original_aut is not None:
        try:
            ic = casc.state_to_config.get(casc.original_aut.get_init_state_number())
            if ic is not None: return ic
        except Exception: pass
    r = reachable_configs(casc); return r[0] if r else None

def reach_to(casc, S, C):
    return reach_strong(S, C, _ff(), C, _tt(), casc, 0)

def trap_configs(casc):
    """Configs mapping (via π = state_of) to an absorbing STATE of D, split into
    (configs at accepting trap states, configs at rejecting trap states)."""
    aut = casc.original_aut
    reach = reachable_configs(casc)
    acc_sink, rej_sink = set(), set()
    for s in range(aut.num_states()):
        outs = list(aut.out(s))
        if outs and all(e.dst == s for e in outs):       # absorbing state s->s
            mk = spot.mark_t()
            for e in outs: mk |= e.acc
            (acc_sink if aut.acc().accepting(mk) else rej_sink).add(s)
    acc_abs = [C for C in reach if casc.state_of(C) in acc_sink]
    rej_abs = [C for C in reach if casc.state_of(C) in rej_sink]
    return acc_abs, rej_abs

fs = {fs!r}; cls = {cls!r}
info = {{"formula": fs, "class": cls}}
try:
    aut = spot.formula(fs).translate()
    casc = decompose_aut(_to_split_form(aut))
    iota = init_config(casc)
    acc_abs, rej_abs = trap_configs(casc)
    info["acc_traps"] = [list(c) for c in acc_abs]
    info["rej_traps"] = [list(c) for c in rej_abs]
    if cls == "safety":
        phi = _simp_f(_And(*[_Not(reach_to(casc, iota, C)) for C in rej_abs])) if rej_abs else _tt()
    else:  # guarantee
        phi = _simp_f(_Or(*[reach_to(casc, iota, C) for C in acc_abs])) if acc_abs else _ff()
    info["looping_size"] = sizes(phi)
    print("BUILD_JSON:" + json.dumps(info), flush=True)
    orig = spot.formula(fs).translate("Buchi")
    info["equiv_orig"] = bool(spot.are_equivalent(orig, phi.translate("Buchi")))
except Exception as e:
    info["error"] = str(e)[:160]; info["tb"] = traceback.format_exc()[-220:]
print("RESULT_JSON:" + json.dumps(info))
'''
    timed_out = False
    try:
        proc = subprocess.run([sys.executable, "-c", child], capture_output=True,
                              text=True, timeout=BUDGET, cwd=PROJECT_ROOT)
        out = (proc.stdout or "") + (proc.stderr or ""); rc = proc.returncode
    except subprocess.TimeoutExpired as e:
        out = ""
        if e.stdout: out += e.stdout if isinstance(e.stdout, str) else e.stdout.decode("utf-8", "replace")
        if e.stderr: out += e.stderr if isinstance(e.stderr, str) else e.stderr.decode("utf-8", "replace")
        rc, timed_out = None, True
    final = build = None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("RESULT_JSON:"): final = json.loads(s[len("RESULT_JSON:"):])
        elif s.startswith("BUILD_JSON:"): build = json.loads(s[len("BUILD_JSON:"):])
    if final is not None: return final
    if build is not None:
        build["equiv_orig"] = "SPOT_TIMEOUT"; return build
    if timed_out: return {"formula": fs, "error": f"BUILD TIMEOUT >{BUDGET}s"}
    if rc == 139: return {"formula": fs, "error": "SEGV (rc 139)"}
    return {"formula": fs, "error": "no marker", "head": out[:200]}


def main():
    print(f"=== dedicated looping dispatch fact-finding (subproc isolated, "
          f"{BUDGET}s/case) ===\n")
    print(f"  {'formula':16s} {'class':10s} {'#traps(acc/rej)':16s} {'equiv':7s} "
          f"{'looping DAG/tree/temp':22s}")
    print("  " + "-" * 84)
    for fs, cls in CASES:
        r = run_case(fs, cls)
        if "error" in r:
            print(f"  {fs:16s} {cls:10s} ERROR: {r['error']}")
            continue
        s = r.get("looping_size")
        ss = f"{s[0]}/{s[1]}/{s[2]}" if s else "-"
        eq = {True: "True", False: "FALSE", "SPOT_TIMEOUT": "SPOTto"}.get(r.get("equiv_orig"), "-")
        traps = f"{len(r.get('acc_traps',[]))}/{len(r.get('rej_traps',[]))}"
        print(f"  {fs:16s} {cls:10s} {traps:16s} {eq:7s} {ss:22s}")
        if r.get("equiv_orig") is False:
            print(f"      !!! NOT EQUIVALENT — acc_traps={r.get('acc_traps')} rej_traps={r.get('rej_traps')}")


if __name__ == "__main__":
    main()
