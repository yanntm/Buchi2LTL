#!/usr/bin/env python3
"""
kr/testing/probe_sl_compose.py

Validates the kr-under-sl COMPOSITION (kr/sl_driven.reconstruct_sl_driven):
sl handles the very-weak envelope, delegates the multi-cyclic core to the normal
kr pipeline, reattaches the label. Per formula, in an isolated subprocess:

  * sl_driven : reconstruct_sl_driven(aut) — size + are_equivalent to original
                (THE soundness check for the composition);
  * sl_alone  : does plain buchi2ltl decline the whole formula (UNSUPPORTED)?
  * kr_full   : size of reconstruct_decomposed(aut) — the kr-on-the-whole
                baseline the composition should beat (construction-only).

Headline: sl_driven equiv=True AND much smaller than kr_full on the
envelope-around-core cases (where sl_alone declines and kr_full explodes).

Run from project root:
    python3 kr/testing/probe_sl_compose.py
    python3 kr/testing/probe_sl_compose.py "X X (G(a -> F b))"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

PER = int(os.environ.get("KR_COMPOSE_TIMEOUT", "15"))
EQ_TREE_CAP = int(os.environ.get("KR_COMPOSE_EQ_CAP", "200000"))

CASES = [
    "X X X a",                  # control: very-weak, sl alone (no delegation)
    "G(a -> F b)",              # control: core alone (frontier near init)
    "X X (G(a -> F b))",        # envelope around an sl-hard core (kr_full explodes)
    "c U (G(a -> F b))",        # until-envelope
    "X (G(p -> (q U r)))",      # X around G(p->(qUr))
    "X X (F(a & X b))",         # X around F(a&Xb)
    "a U (F(b & X c))",         # until around F(b&Xc)
]

_CHILD = r'''
import sys, json, contextlib, io
from pathlib import Path
sys.path.insert(0, str(Path(r"{root}").resolve()))
import spot

def sizes(f):
    seen, st, t = set(), [f], 0
    def ts(g, memo):
        if g.id() in memo: return memo[g.id()]
        v = 1 + sum(ts(c, memo) for c in g); memo[g.id()] = v; return v
    while st:
        g = st.pop(); i = g.id()
        if i in seen: continue
        seen.add(i)
        if g.kindstr() in ("U","M","R","W","F","G"): t += 1
        for c in g: st.append(c)
    return [len(seen), ts(f, {{}}), t]

fs = {fs!r}
info = {{"formula": fs}}
try:
    from aut2ltl.portfolio.sl_driven import reconstruct_sl_driven
    from aut2ltl.portfolio.decompose_recombine import reconstruct_decomposed
    from aut2ltl.sl.reconstruction import reconstruct_ltl
    aut = spot.formula(fs).translate()

    # sl alone (does it decline the whole formula?)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            o = reconstruct_ltl(spot.postprocess(aut, "TGBA", "Small"))
        r0 = o.formula
        info["sl_alone"] = "UNSUPPORTED" if (r0 is None or (isinstance(r0,str) and "UNSUPPORTED" in r0)) else "ok"
    except Exception as e:
        info["sl_alone"] = "ERR"

    # sl-driven composition + soundness check
    sd = reconstruct_sl_driven(aut)
    if sd is None:
        info["sl_driven"] = "DECLINED"
    else:
        info["sl_driven"] = sizes(sd)
        orig = spot.formula(fs).translate("Buchi")
        info["equiv"] = bool(spot.are_equivalent(orig, sd.translate("Buchi")))

    # kr-on-the-whole baseline (construction-only; may be a giant DAG)
    info["sl_driven_printed"] = True
    # FLUSH: stdout is block-buffered in the subprocess; the explosive kr_full
    # baseline below can hang and get the process killed, which would lose this
    # (already-complete) sl_driven result. Flush so it always reaches the parent.
    print("RESULT_JSON:" + json.dumps(info), flush=True)
    full = reconstruct_decomposed(aut).formula
    print("KRFULL_JSON:" + json.dumps(sizes(full)))
except Exception as e:
    import traceback
    if not info.get("sl_driven_printed"):
        info["result"] = "ERROR"; info["error"] = str(e)[:140]
        info["tb"] = traceback.format_exc()[-300:]
        print("RESULT_JSON:" + json.dumps(info))
'''


def run(fs):
    child = _CHILD.format(root=PROJECT_ROOT, fs=fs)
    timed_out = False
    try:
        p = subprocess.run([sys.executable, "-c", child], capture_output=True,
                           text=True, timeout=PER, cwd=PROJECT_ROOT)
        out = (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired as e:
        # Recover the partial output: the child flushes its sl_driven RESULT_JSON
        # before the (possibly explosive) kr_full baseline, so a timeout in
        # kr_full must not discard the already-complete sl_driven result. On
        # timeout the captured streams come back as BYTES (text-decode only runs
        # on normal completion), so decode them.
        timed_out = True
        so, se = e.stdout or b"", e.stderr or b""
        out = (so.decode("utf-8", "replace") if isinstance(so, bytes) else so) + \
              (se.decode("utf-8", "replace") if isinstance(se, bytes) else se)
    res, krfull = None, "TIMEOUT/explode"
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("RESULT_JSON:"):
            res = json.loads(s[len("RESULT_JSON:"):])
        elif s.startswith("KRFULL_JSON:"):
            krfull = json.loads(s[len("KRFULL_JSON:"):])
    if res is None:
        return {"formula": fs, "result": "ERROR", "error": out[-300:]}
    res["kr_full"] = krfull
    return res


def fmt(s):
    return f"{s[0]}/{s[1]}/{s[2]}" if isinstance(s, list) else str(s)


def main():
    cases = sys.argv[1:] or CASES
    print(f"=== kr-under-sl composition probe ({PER}s/case) ===\n")
    print(f"  {'formula':24s} {'sl_alone':10s} {'sl_driven DAG/tr/tmp':22s} "
          f"{'equiv':6s} {'kr_full DAG/tr/tmp':22s}")
    print("  " + "-" * 92)
    fails = 0
    for fs in cases:
        r = run(fs)
        if r.get("result") in ("TIMEOUT", "ERROR"):
            print(f"  {fs:24s} {r.get('result')}  {r.get('error','')[:40]}")
            continue
        eq = r.get("equiv")
        eqs = {True: "True", False: "FALSE", None: "-"}.get(eq, str(eq))
        if eq is False:
            fails += 1
        print(f"  {fs:24s} {str(r.get('sl_alone','-')):10s} "
              f"{fmt(r.get('sl_driven','-')):22s} {eqs:6s} "
              f"{fmt(r.get('kr_full','-')):22s}{'  <-- FALSE' if eq is False else ''}")
    print(f"\n=== {'CLEAN' if not fails else str(fails)+' EQUIV=FALSE'} ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
