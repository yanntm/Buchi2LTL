#!/usr/bin/env python3
"""
kr/testing/probe_cobuchi_dispatch.py

Fact-finding for the coBüchi (persistence, Σ₂) acceptance dispatch — the mirror
of the wired Büchi dispatch (kr/acceptance_dispatch.reconstruct_buchi).

CRUCIAL: this probe runs UNDER the decomposition front end, the GOTO path. The
dispatch never sees the raw translate() automaton — it sees each piece that
`reconstruct_decomposed` produces via `_to_split_form` (deterministic-generic +
sat_minimize) then the AND/OR split. We therefore reuse `reconstruct_decomposed`
with a coBüchi `reconstruct` callable, exactly as the real wiring would, so the
sizes are the ones we would actually ship (sat_minimize can shrink the automaton
a lot, e.g. the FGa|FGb absorption case).

The candidate form is  φ := ⋀_{C∈α} Fin(C)  with α = the "must be visited
finitely" configs, read COVER-AWARE off the pruned config aut as the configs
whose lifted marks make `g.acc()` REJECT (the symmetric dual of the Büchi reader
which keeps the ones that make it ACCEPT).

Reports, per case: the split kind; the acceptance class BOTH on the
`_to_split_form` det-generic automaton (pre-parity — where a real coBüchi gate
could live) AND on the parity-normalized cascade the dispatch hook actually sees
(`is_co_buchi`/`is_buchi`); the built size (DAG/tree/temporals); and equivalence
to the ORIGINAL. BUILD and EQUIV are budgeted separately (BUILD_JSON is emitted
before the equiv attempt) so a translate/32-acc-cap timeout is reported as
SPOT_TIMEOUT with the size intact, NOT conflated with a construction timeout.

Per case in an isolated subprocess with a budget (a blown budget IS a finding).
Run from project root (prefer backgrounding it, no long foreground timeout):
    python3 kr/testing/probe_cobuchi_dispatch.py
    python3 kr/testing/probe_cobuchi_dispatch.py "FGa | FGb"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

BUDGET = int(os.environ.get("KR_PROBE_TIMEOUT", "15"))

# Persistence / coBüchi candidates. (The gate's exclusion of recurrence is shown
# by the `gate` column being False there and is asserted in the module docstring;
# we don't run a recurrence case through the un-gated ⋀Fin form here.)
CASES = [
    "FGa", "F(a & G b)", "FG(a | b)", "FGa | FGb", "F G a | F G b | F G c",
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
from kr.fin import fin_c
from kr.ltl_builders import _And, _simp_f, _tree_size_f

def sizes(f):
    seen, kinds, st = set(), {{}}, [f]
    while st:
        g = st.pop(); i = g.id()
        if i in seen: continue
        seen.add(i); k = g.kindstr(); kinds[k] = kinds.get(k, 0) + 1
        for c in g: st.append(c)
    temp = sum(v for k, v in kinds.items() if k in ("U","M","R","W","F","G"))
    return [len(seen), _tree_size_f(f), temp]

def cobuchi_finite_configs(casc):
    """Cover-aware α: reachable configs whose lifted marks make g.acc() REJECT
    (the must-be-finite set). Dual of buchi_accepting_configs."""
    g = build_pruned_config_aut(casc)
    if g is None: return []
    reach = reachable_configs(casc)
    acc = g.acc()
    out = []
    for i in range(g.num_states()):
        mk = spot.mark_t()
        for e in g.out(i): mk |= e.acc
        if not acc.accepting(mk):
            out.append(reach[i])
    return out

def cobuchi_reconstruct(casc):
    """Per-piece coBüchi reconstruct, fed to reconstruct_decomposed in place of
    the Muller path so the whole build runs UNDER decomposition."""
    alpha = sorted(cobuchi_finite_configs(casc))
    return _simp_f(_And(*[fin_c(c, casc) for c in alpha])) if alpha else spot.formula.tt()

fs = {fs!r}
info = {{"formula": fs}}
try:
    aut = spot.formula(fs).translate()
    # acc class on the decomposition's normalized automaton (pre-parity, generic)
    det = _to_split_form(aut)
    da = det.acc()
    info["split"] = "%s(%d)" % split_report(aut)
    info["det_acc"] = str(det.get_acceptance())
    info["det_is_buchi"] = bool(da.is_buchi())
    info["det_is_co_buchi"] = bool(da.is_co_buchi())
    # acc class on the parity-normalized cascade the dispatch hook actually sees
    casc0 = decompose_aut(det if det.num_states() else aut)
    ca = casc0.original_aut.acc()
    info["casc_acc"] = str(casc0.original_aut.get_acceptance())
    info["casc_is_buchi"] = bool(ca.is_buchi())
    info["casc_is_co_buchi"] = bool(ca.is_co_buchi())
    # CANDIDATE GATE the dispatch hook can run with ONLY the parity cascade in
    # hand: recover the natural acceptance via postprocess->GENERIC (what
    # _to_split_form does — the parity step mangled Fin(0) into Inf(0)|Fin(1),
    # is_co_buchi False) and test is_co_buchi on THAT. Must be True for
    # persistence, False for recurrence (GFa). (postprocess->coBuchi is UNSOUND
    # here: GFa passes it.)
    try:
        _gen = spot.postprocess(casc0.original_aut, "deterministic", "generic")
        info["casc_cobuchi_recog"] = bool(_gen.acc().is_co_buchi())
    except Exception as _e:
        info["casc_cobuchi_recog"] = "err:" + str(_e)[:40]
    # --- BUILD under decomposition; emit size BEFORE the equiv attempt ---
    phi = reconstruct_decomposed(aut, reconstruct=cobuchi_reconstruct).formula
    info["cobuchi_size"] = sizes(phi)
    info["built"] = True
    print("BUILD_JSON:" + json.dumps(info), flush=True)
    # --- EQUIV (the 32-acc-cap translate wall lives here, not in BUILD) ---
    orig = spot.formula(fs).translate("Buchi")
    info["equiv_orig"] = bool(spot.are_equivalent(orig, phi.translate("Buchi")))
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
        build["equiv_orig"] = "SPOT_TIMEOUT"   # build done, equiv/translate blew budget
        return build
    if timed_out:
        return {"formula": fs, "error": f"BUILD TIMEOUT >{BUDGET}s (construction blew budget)"}
    if rc == 139:
        return {"formula": fs, "error": "SEGV (rc 139)"}
    return {"formula": fs, "error": "no marker", "head": out[:200]}


def main():
    cases = sys.argv[1:] or CASES
    print(f"=== coBüchi dispatch fact-finding, UNDER decomposition "
          f"(subproc isolated, {BUDGET}s/case) ===\n")
    print(f"  {'formula':20s} {'split':8s} {'det_acc':16s} {'det.co':6s} "
          f"{'casc_acc':16s} {'gate':5s} {'equiv':7s} {'DAG/tree/temp':20s}")
    print("  " + "-" * 110)
    for fs in cases:
        r = run_case(fs)
        if "error" in r:
            print(f"  {fs:20s} ERROR: {r['error']}")
            continue
        s = r.get("cobuchi_size")
        ss = f"{s[0]}/{s[1]}/{s[2]}" if s else "-"
        eq = {True: "True", False: "FALSE", "SPOT_TIMEOUT": "SPOTto"}.get(r.get("equiv_orig"), "-")
        print(f"  {fs:20s} {r.get('split',''):8s} {r.get('det_acc',''):16s} "
              f"{str(r.get('det_is_co_buchi'))[0]:6s} {r.get('casc_acc',''):16s} "
              f"{str(r.get('casc_cobuchi_recog'))[0]:5s} {eq:7s} {ss:20s}")
        if r.get("equiv_orig") is False:
            print(f"      !!! NOT EQUIVALENT — split={r.get('split')} casc_acc={r.get('casc_acc')}")


if __name__ == "__main__":
    main()
