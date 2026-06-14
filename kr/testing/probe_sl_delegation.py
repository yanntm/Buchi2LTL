#!/usr/bin/env python3
"""
kr/testing/probe_sl_delegation.py

Fact-finder for the "kr UNDER sl" idea (full-suffix delegation): sl drives, and
when it hits a state it cannot translate exactly (a MULTI-STATE SCC — single-
state self-loops it handles), it delegates the whole sub-automaton A_q (q as a
fresh initial state) to the normal kr pipeline `reconstruct_decomposed`, then
reattaches the returned label. This probe does NOT wire anything; it measures
whether the idea is viable, in particular:

  * does buchi2ltl decline the whole (envelope-around-core) formula today?
  * what are the multi-state SCCs (sl's hard cases = the delegation targets)?
  * for each SCC entry q, the delegated sub-automaton A_q: HOW MANY FEWER STATES
    than the full automaton (BLS cost ~ cascade depth ~ state count, so peeling a
    prefix and handing kr a SMALLER automaton is the structural win), and does
    kr(A_q) come out small and language-equivalent to A_q?
  * kr(A_q) size vs kr(full): is delegating the core cheaper than kr on the whole?

Per formula in an isolated subprocess, 15s budget. Run from project root:
    python3 kr/testing/probe_sl_delegation.py
    python3 kr/testing/probe_sl_delegation.py "X X (G(a -> F b))"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

PER = int(os.environ.get("KR_PROBE_TIMEOUT", "15"))

# Envelopes around multi-state-SCC cores (sl-UNSUPPORTED cores: G(a->Fb),
# G(p->(qUr)), F(a&Xb)), plus controls (very-weak / core-alone).
CASES = [
    "X X X a",                  # control: very-weak, no multi-state SCC -> no delegation
    "G(a -> F b)",              # control: core alone (frontier near init)
    "X X (G(a -> F b))",        # X-envelope around an sl-hard core
    "c U (G(a -> F b))",        # until-envelope
    "X (G(p -> (q U r)))",      # X around G(p->(qUr))
    "X X (F(a & X b))",         # X around F(a&Xb)
    "G(a -> F b) & X X c",      # conjunctive envelope (product)
]

_CHILD = r'''
import os, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(r"{root}").resolve()))
import spot, contextlib, io

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

def sub_from(aut, q):
    sub = spot.automaton(aut.to_str("hoa"))
    sub.set_init_state(q)
    sub.purge_unreachable_states()
    return sub

fs = {fs!r}
info = {{"formula": fs}}
try:
    from buchi2ltl.reconstruction import reconstruct_ltl
    from kr.decompose_recombine import reconstruct_decomposed

    # Deterministic TGBA: clean A_q semantics (future from q independent of prefix)
    # and the form buchi2ltl/sl operate on.
    aut = spot.postprocess(spot.formula(fs).translate(), "TGBA", "Deterministic")
    info["states"] = aut.num_states()

    # Does sl/buchi2ltl decline the whole formula today?
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            out = reconstruct_ltl(spot.postprocess(aut, "TGBA", "Small"))
        rec = out[0] if isinstance(out,(tuple,list)) else out
        info["sl_whole"] = "UNSUPPORTED" if (rec is None or (isinstance(rec,str) and "UNSUPPORTED" in rec)) else "ok"
    except Exception as e:
        info["sl_whole"] = "ERR:" + str(e)[:40]

    si = spot.scc_info(aut)
    init = aut.get_init_state_number()
    # Multi-state SCCs = sl's hard cases (single-state self-loops sl handles).
    multi = [s for s in range(si.scc_count()) if len(si.states_of(s)) >= 2]
    info["multi_sccs"] = [[int(x) for x in si.states_of(s)] for s in multi]

    # Entry states of each multi-state SCC (incoming edge from outside, or init).
    deleg = []
    for s in multi:
        members = set(int(x) for x in si.states_of(s))
        entries = set()
        if init in members:
            entries.add(init)
        for p in range(aut.num_states()):
            if p in members:
                continue
            for e in aut.out(p):
                if e.dst in members:
                    entries.add(int(e.dst))
        for q in sorted(entries):
            Aq = sub_from(aut, q)
            kq = reconstruct_decomposed(Aq)
            equiv = bool(spot.are_equivalent(Aq, kq.translate()))
            deleg.append({{"q": q, "Aq_states": Aq.num_states(),
                           "kr_Aq": sizes(kq), "equiv": equiv}})
    info["delegations"] = deleg
    info["result"] = "OK"
    # Print the (fast, small) delegation result FIRST so an explosive baseline
    # below cannot hide it. FLUSH: stdout is block-buffered in the subprocess, so
    # without this the buffered line is lost if the kr_full baseline hangs and the
    # process is killed.
    print("RESULT_JSON:" + json.dumps(info), flush=True)
    # Baseline to beat: kr on the FULL automaton. May explode/timeout — that is
    # itself the finding; we already emitted the delegation numbers.
    full = reconstruct_decomposed(aut)
    print("KRFULL_JSON:" + json.dumps(sizes(full)))
except Exception as e:
    import traceback
    if info.get("result") != "OK":
        info["result"] = "ERROR"; info["error"] = str(e)[:140]
        info["tb"] = traceback.format_exc()[-300:]
        print("RESULT_JSON:" + json.dumps(info))
'''


def run(fs):
    child = _CHILD.format(root=PROJECT_ROOT, fs=fs)
    try:
        p = subprocess.run([sys.executable, "-c", child], capture_output=True,
                           text=True, timeout=PER, cwd=PROJECT_ROOT)
        out = (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired as e:
        # Recover the flushed delegation RESULT_JSON: a hang in the explosive
        # kr_full baseline must not discard the already-emitted result. Streams
        # come back as BYTES on timeout, so decode.
        so, se = e.stdout or b"", e.stderr or b""
        out = (so.decode("utf-8", "replace") if isinstance(so, bytes) else so) + \
              (se.decode("utf-8", "replace") if isinstance(se, bytes) else se)
    res = None
    krfull = "TIMEOUT/explode"
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


def main():
    cases = sys.argv[1:] or CASES
    for fs in cases:
        r = run(fs)
        print(f"\n=== {fs} ===")
        if r.get("result") != "OK":
            print(f"    {r.get('result')}: {r.get('error','')}")
            continue
        n = r["states"]
        kf = r["kr_full"]
        kfs = f"{kf[0]}/{kf[1]}/{kf[2]}" if isinstance(kf, list) else str(kf)
        print(f"    states={n}  sl_whole={r['sl_whole']}  "
              f"kr_full DAG/tree/temp={kfs}")
        print(f"    multi-state SCCs (delegation targets): {r['multi_sccs'] or 'none'}")
        for d in r["delegations"]:
            kq = d["kr_Aq"]
            red = n - d["Aq_states"]
            print(f"      delegate q={d['q']:2d}: A_q states={d['Aq_states']} "
                  f"(−{red} vs full)  kr(A_q)={kq[0]}/{kq[1]}/{kq[2]}  "
                  f"equiv={d['equiv']}")


if __name__ == "__main__":
    main()
