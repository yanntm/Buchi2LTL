#!/usr/bin/env python3
"""
kr/testing/probe_weak_dispatch.py

Fact-finding for the WEAK (Δ₁) / looping (Σ₁/Π₁) acceptance dispatch — the last
hierarchy class, after the wired Büchi (Π₂) and coBüchi (Σ₂). Per construction
-ref §9.3, a deterministic WEAK cascade (every SCC entirely accepting or entirely
rejecting) gets a direct form with NO Fin at all, only `reach_to`:

    reach_to(ι, C) := reach(ι, C, false, C, true) = reach_strong(ι,C,⊥,C,⊤)
    end_in(G) := ( ⋁_{C∈H}  reach_to(ι,C) ) ∧ ( ⋀_{C'∈G'} ¬reach_to(ι,C') )
    φ_weak    := ⋁ over accepting SCC G of the config aut : end_in(G)     (Δ₁)

where H = configs of the accepting SCC G, G' = configs reachable from G but not
in G (so the run must SETTLE in G). Looping-Büchi (safety, single rejecting sink)
and looping-coBüchi (guarantee, single accepting sink) are the special cases.

WHY this might matter: safety/guarantee walls (`G(a->Xb)`, `G(a->Xa)`, `F(a&Xb)`)
are currently handled by the Büchi dispatch (⋁¬Fin), where `Fin` drags in the
`reach_to⁺(C,C)` self-loop machinery. The weak form is pure `reach_to` — possibly
far smaller. (Open: the reach explosion itself — the τ-tail key-space problem —
lives in `reach_to`, so this may NOT crack the reach walls; the probe measures it.)

Runs UNDER decomposition (the GOTO path), BUILD and EQUIV budgeted separately.
Gate fact-finding: reports `is_weak_automaton` on BOTH the parity cascade and the
_to_split_form generic automaton (the parity step may destroy weakness, exactly as
it hid coBüchi). A case the gate calls NOT weak is reported `declined` (no build,
no spurious FALSE).

Per case in an isolated subprocess with a budget (a blown budget IS a finding).
Run from project root (prefer backgrounding it):
    python3 kr/testing/probe_weak_dispatch.py
    python3 kr/testing/probe_weak_dispatch.py "G(a -> X b)"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

BUDGET = int(os.environ.get("KR_PROBE_TIMEOUT", "15"))

CASES = [
    # safety (looping-Büchi, Π₁)
    "Ga", "G(a | b)", "G(a -> X b)", "Ga | Gb", "G(a -> X a)",
    # guarantee (looping-coBüchi, Σ₁)
    "Fa", "a U b", "F(a & b)", "F(a & X b)",
    # obligation (weak, Δ₁)
    "Fa | Gb", "Fa & Gb", "(a U b) | Gc", "Ga | Fb",
    # controls — NOT weak (recurrence/persistence/reach): gate must decline
    "GFa", "FGa", "G(p -> (q U r))",
]


def run_case(fs: str) -> dict:
    child = f'''
import os, sys, json, traceback
from pathlib import Path
sys.path.insert(0, str(Path(r"{PROJECT_ROOT}").resolve()))
import spot
from kr import decompose_aut
from kr.decompose_recombine import reconstruct_decomposed, _to_split_form, split_report
from kr.config_graph import build_pruned_config_aut, reachable_configs
from kr.reachability_operators import reach_strong
from kr.ltl_builders import _And, _Or, _Not, _tt, _ff, _simp_f, _tree_size_f

def sizes(f):
    seen, kinds, st = set(), {{}}, [f]
    while st:
        g = st.pop(); i = g.id()
        if i in seen: continue
        seen.add(i); k = g.kindstr(); kinds[k] = kinds.get(k, 0) + 1
        for c in g: st.append(c)
    temp = sum(v for k, v in kinds.items() if k in ("U","M","R","W","F","G"))
    return [len(seen), _tree_size_f(f), temp]

def is_weak(aut):
    try:
        return bool(spot.is_weak_automaton(aut))
    except Exception:
        try:
            return bool(aut.prop_weak().is_true())
        except Exception:
            return False

def init_config(casc):
    if casc.original_aut is not None:
        try:
            ic = casc.state_to_config.get(casc.original_aut.get_init_state_number())
            if ic is not None:
                return ic
        except Exception:
            pass
    r = reachable_configs(casc)
    return r[0] if r else None

def reach_to(casc, S, C):
    return reach_strong(S, C, _ff(), C, _tt(), casc, 0)

def weak_form(casc):
    """φ_weak = ⋁ over accepting SCC G of the pruned config aut : end_in(G)."""
    g = build_pruned_config_aut(casc)
    if g is None:
        return _ff()
    reach = reachable_configs(casc)         # node i <-> reach[i]
    iota = init_config(casc)
    si = spot.scc_info(g)
    terms = []
    for i in range(si.scc_count()):
        if si.is_rejecting_scc(i):
            continue
        nodes = [k for k in range(g.num_states()) if si.scc_of(k) == i]
        nodeset = set(nodes)
        # G' = reachable from G, not in G (BFS over g)
        visited, stack, gprime = set(nodes), list(nodes), set()
        while stack:
            u = stack.pop()
            for e in g.out(u):
                if e.dst not in visited:
                    visited.add(e.dst)
                    if e.dst not in nodeset:
                        gprime.add(e.dst)
                    stack.append(e.dst)
        reach_in = _Or(*[reach_to(casc, iota, reach[k]) for k in nodes])
        avoid_out = _And(*[_Not(reach_to(casc, iota, reach[k])) for k in gprime]) if gprime else _tt()
        terms.append(_And(reach_in, avoid_out))
    return _simp_f(_Or(*terms)) if terms else _ff()

fs = {fs!r}
info = {{"formula": fs}}
try:
    aut = spot.formula(fs).translate()
    det = _to_split_form(aut)
    info["split"] = "%s(%d)" % split_report(aut)
    info["det_acc"] = str(det.get_acceptance())
    info["det_is_weak"] = is_weak(det)
    casc0 = decompose_aut(det if det.num_states() else aut)
    info["casc_is_weak"] = is_weak(casc0.original_aut)
    info["gate"] = info["det_is_weak"]      # candidate gate: weakness on the generic aut
    if not info["gate"]:
        info["declined"] = True
        print("RESULT_JSON:" + json.dumps(info)); raise SystemExit
    # --- BUILD under decomposition; emit size BEFORE equiv ---
    phi = reconstruct_decomposed(aut, reconstruct=weak_form).formula
    info["weak_size"] = sizes(phi)
    info["built"] = True
    print("BUILD_JSON:" + json.dumps(info), flush=True)
    orig = spot.formula(fs).translate("Buchi")
    info["equiv_orig"] = bool(spot.are_equivalent(orig, phi.translate("Buchi")))
except SystemExit:
    pass
except Exception as e:
    info["error"] = str(e)[:160]
    info["tb"] = traceback.format_exc()[-220:]
print("RESULT_JSON:" + json.dumps(info))
'''
    timed_out = False
    try:
        proc = subprocess.run([sys.executable, "-c", child], capture_output=True,
                              text=True, timeout=BUDGET, cwd=PROJECT_ROOT)
        out = (proc.stdout or "") + (proc.stderr or "")
        rc = proc.returncode
    except subprocess.TimeoutExpired as e:
        out = ""
        if e.stdout:
            out += e.stdout if isinstance(e.stdout, str) else e.stdout.decode("utf-8", "replace")
        if e.stderr:
            out += e.stderr if isinstance(e.stderr, str) else e.stderr.decode("utf-8", "replace")
        rc, timed_out = None, True
    final = build = None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("RESULT_JSON:"):
            final = json.loads(s[len("RESULT_JSON:"):])
        elif s.startswith("BUILD_JSON:"):
            build = json.loads(s[len("BUILD_JSON:"):])
    if final is not None:
        return final
    if build is not None:
        build["equiv_orig"] = "SPOT_TIMEOUT"
        return build
    if timed_out:
        return {"formula": fs, "error": f"BUILD TIMEOUT >{BUDGET}s (construction blew budget)"}
    if rc == 139:
        return {"formula": fs, "error": "SEGV (rc 139)"}
    return {"formula": fs, "error": "no marker", "head": out[:200]}


def main():
    cases = sys.argv[1:] or CASES
    print(f"=== weak/looping dispatch fact-finding, UNDER decomposition "
          f"(subproc isolated, {BUDGET}s/case) ===\n")
    print(f"  {'formula':20s} {'split':8s} {'det_acc':18s} {'gate':5s} "
          f"{'equiv':7s} {'weak DAG/tree/temp':20s}")
    print("  " + "-" * 96)
    for fs in cases:
        r = run_case(fs)
        if "error" in r:
            print(f"  {fs:20s} ERROR: {r['error']}")
            continue
        if r.get("declined"):
            print(f"  {fs:20s} {r.get('split',''):8s} {r.get('det_acc',''):18s} "
                  f"{'F':5s} {'declined':7s}")
            continue
        s = r.get("weak_size")
        ss = f"{s[0]}/{s[1]}/{s[2]}" if s else "-"
        eq = {True: "True", False: "FALSE", "SPOT_TIMEOUT": "SPOTto"}.get(r.get("equiv_orig"), "-")
        print(f"  {fs:20s} {r.get('split',''):8s} {r.get('det_acc',''):18s} "
              f"{str(r.get('gate'))[0]:5s} {eq:7s} {ss:20s}")
        if r.get("equiv_orig") is False:
            print(f"      !!! NOT EQUIVALENT — split={r.get('split')} det_acc={r.get('det_acc')}")


if __name__ == "__main__":
    main()
