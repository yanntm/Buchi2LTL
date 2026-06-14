#!/usr/bin/env python3
"""
kr/testing/probe_acc_dispatch.py

Rebuild + validate the config-indexed Acc(c) construction for the BOUNDED /
transient fragment (the X-ladder), reconstructed from the spec recorded in
kr/dag_folding.md "Key-space diagnosis" (the original POC was reverted
uncommitted). The idea: bypass the cascade reach machinery entirely on inputs
where the run reaches a ⊤/⊥ sink within a bounded horizon, so the answer is a
finite unrolling — the literal small formula — instead of the τ-tail explosion.

    Acc(c) = language of D from configuration c, memoized per config:
      R1 (base):     ⊤ if L(D from state_of(c)) is universal,
                     ⊥ if it is empty                         (Spot ⊤/⊥ oracle)
      R2 (unroll):   ⋁_σ  guard(σ) ∧ X Acc(move_config(c, σ))  (transient c)
      cycle:         a config re-entered on the unroll path that is NOT ⊤/⊥ is
                     RECURRENT ⇒ Acc declines (returns None ⇒ caller uses BLS).

    φ := Acc(ι).

Self-gating: R1-then-cycle means Acc returns a formula only when every path
hits ⊤/⊥ before revisiting a state — i.e. the bottom/bounded class. Ga (live
self-loop), a U b / F(..) (wait-loop) are recurrent ⇒ declined, correctly.

Validation targets (dag_folding.md): Xa&XXa 23676→4, Xa&XXXa 234k→5, equiv True;
the X(a&Xa) reach wall (1.5e9 under BLS) should collapse; recurrent controls must
decline. Per case in an isolated subprocess, BUILD/EQUIV budgeted separately.

Run from project root (prefer backgrounding it):
    python3 kr/testing/probe_acc_dispatch.py
    python3 kr/testing/probe_acc_dispatch.py "X(a & X a)"
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
    # bounded / bottom fragment — Acc should FIRE and collapse to the literal
    "a", "X a", "X X a", "X X X a", "a & X a", "X(a & X a)", "X a & X X a", "a | X b",
    # recurrent controls — Acc must DECLINE (return None -> BLS)
    "Ga", "a U b", "F(a & b)", "G(a -> X b)", "GFa", "FGa",
]


def run_case(fs: str) -> dict:
    child = f'''
import os, sys, json, traceback
from pathlib import Path
sys.path.insert(0, str(Path(r"{PROJECT_ROOT}").resolve()))
import spot
from aut2ltl.kr import decompose_aut, reconstruct_bls
from aut2ltl.kr.ltl_builders import _And, _Or, _X, _tt, _ff, _simp_f, _tree_size_f, _letters_to_f

def sizes(f):
    seen, kinds, st = set(), {{}}, [f]
    while st:
        g = st.pop(); i = g.id()
        if i in seen: continue
        seen.add(i); k = g.kindstr(); kinds[k] = kinds.get(k, 0) + 1
        for c in g: st.append(c)
    temp = sum(v for k, v in kinds.items() if k in ("U","M","R","W","F","G"))
    return [len(seen), _tree_size_f(f), temp]

class _Recurrent(Exception): pass

def reconstruct_acc(casc):
    """φ = Acc(ι), or None if any path is recurrent (not the bounded fragment)."""
    D = casc.original_aut
    if D is None: return None
    # ⊤/⊥ oracle per state, precomputed (small automaton; bounded Spot calls).
    Dc = spot.automaton(D.to_str("hoa"))
    true_aut = spot.formula("1").translate()
    empty_q, univ_q = {{}}, {{}}
    for q in range(D.num_states()):
        Dc.set_init_state(q)
        e = Dc.is_empty()
        empty_q[q] = e
        univ_q[q] = (not e) and bool(spot.are_equivalent(Dc, true_aut))
    # initial config
    iota = None
    try:
        iota = casc.state_to_config.get(D.get_init_state_number())
    except Exception:
        pass
    if iota is None:
        r = casc.reachable_configs(); iota = r[0] if r else None
    if iota is None: return None
    nl = casc.num_letters()
    memo, stack = {{}}, set()
    def acc(c):
        if c in memo: return memo[c]
        q = casc.state_of(c)
        if q is not None and empty_q.get(q): memo[c] = _ff(); return memo[c]
        if q is not None and univ_q.get(q): memo[c] = _tt(); return memo[c]
        if c in stack: raise _Recurrent()
        stack.add(c)
        terms = []
        for li in range(nl):
            g = _letters_to_f(casc.letter_valuations[li], casc.aps)
            terms.append(_And(g, _X(acc(casc.move_config(c, li)))))
        stack.discard(c)
        memo[c] = _simp_f(_Or(*terms))
        return memo[c]
    try:
        return acc(iota)
    except _Recurrent:
        return None

fs = {fs!r}
info = {{"formula": fs}}
try:
    aut = spot.formula(fs).translate()
    casc = decompose_aut(aut)
    phi = reconstruct_acc(casc)
    if phi is None:
        info["declined"] = True
        print("RESULT_JSON:" + json.dumps(info)); raise SystemExit
    info["acc_size"] = sizes(phi)
    info["bls_size"] = sizes(reconstruct_bls(casc))   # BLS baseline for A/B
    print("BUILD_JSON:" + json.dumps(info), flush=True)
    orig = spot.formula(fs).translate("Buchi")
    info["equiv_orig"] = bool(spot.are_equivalent(orig, phi.translate("Buchi")))
except SystemExit:
    pass
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
    cases = sys.argv[1:] or CASES
    print(f"=== Acc(c) bounded-fragment dispatch (subproc isolated, {BUDGET}s/case) ===\n")
    print(f"  {'formula':16s} {'fired':6s} {'equiv':7s} {'acc DAG/tree/temp':20s} "
          f"{'bls DAG/tree/temp':20s}")
    print("  " + "-" * 78)
    for fs in cases:
        r = run_case(fs)
        if "error" in r:
            print(f"  {fs:16s} ERROR: {r['error']}")
            continue
        if r.get("declined"):
            print(f"  {fs:16s} {'no':6s} {'(BLS)':7s}")
            continue
        a = r.get("acc_size"); b = r.get("bls_size")
        asz = f"{a[0]}/{a[1]}/{a[2]}" if a else "-"
        bsz = f"{b[0]}/{b[1]}/{b[2]}" if b else "-"
        eq = {True: "True", False: "FALSE", "SPOT_TIMEOUT": "SPOTto"}.get(r.get("equiv_orig"), "-")
        print(f"  {fs:16s} {'YES':6s} {eq:7s} {asz:20s} {bsz:20s}")
        if r.get("equiv_orig") is False:
            print(f"      !!! NOT EQUIVALENT")


if __name__ == "__main__":
    main()
