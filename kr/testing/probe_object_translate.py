#!/usr/bin/env python3
"""
kr/testing/probe_object_translate.py

Can Spot translate our recovered formula DIRECTLY from the hash-consed
spot.formula DAG, where the default string-shaped pipeline blows up?

Hypothesis (user): the Couvreur FM construction (ltl_to_tgba_fm) works
structurally on the formula object; since spot.formula is hash-consed,
identical subformulas are pointer-identical and the tableau should benefit
from sharing — no flat unfolding ever happens. If true, Spot-side
verification comes back for the cases currently reported SPOT_TIMEOUT
(the flat-string path) without waiting on upstream sharing-aware work.

Methods compared (one subprocess per case x method; the parent timeout is
the real budget — SIGALRM cannot fire inside Spot's C++):
    fm        — spot.ltl_to_tgba_fm(f, dict_of_original)  (Couvreur, direct)
    low_any   — spot.translate(f, "low", "any")           (minimal postproc)
    default   — spot.translate(f, "Buchi")                (current path)
    trans_cls — spot.translator() TGBA/Small .run(f)      (class API, user suggestion)

Each child: construct cascade + formula object (timed), translate (timed),
then are_equivalent vs the original (timed). A blown budget or a
too-many-acceptance-sets error IS the finding — printed per phase, flushed,
so partial output names the wall.

Run from project root (each case stays inside the small-probe budget):
    python3 kr/testing/probe_object_translate.py                 # default cases
    python3 kr/testing/probe_object_translate.py "Ga | Gb"       # specific
    KR_PROBE_TIMEOUT=12 python3 kr/testing/probe_object_translate.py
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

PROBE_TIMEOUT = int(os.environ.get("KR_PROBE_TIMEOUT", "12"))

# Known SPOT_TIMEOUT / 32-acc-set ladder cases (construction itself is fast).
DEFAULT_CASES = [
    "G(a -> X b)",
    "Ga | Gb",
    "G(a -> X a)",
]

METHODS = ["fm", "low_any", "default", "trans_cls"]

_CHILD = '''
import sys, time
import spot
from pathlib import Path
proj = Path(r"{proj}").resolve()
sys.path.insert(0, str(proj))
from kr import decompose_aut, reconstruct_ltl_paper_style

fs = {fs!r}
method = {method!r}

f = spot.formula(fs)
orig = f.translate("Buchi")

t0 = time.monotonic()
casc = decompose_aut(f.translate())
rec_f = reconstruct_ltl_paper_style(casc)
print(f"PHASE construct ok {{time.monotonic()-t0:.2f}}s", flush=True)

# quick DAG stats (sharing-aware; never unfolds)
seen, stack, n_temporal = set(), [rec_f], 0
while stack:
    g = stack.pop()
    if g.id() in seen:
        continue
    seen.add(g.id())
    if g.kindstr() in ("U", "M", "R", "W", "F", "G"):
        n_temporal += 1
    stack.extend(g)
print(f"PHASE dag nodes={{len(seen)}} temporal={{n_temporal}}", flush=True)

t0 = time.monotonic()
try:
    if method == "fm":
        aut = spot.ltl_to_tgba_fm(rec_f, orig.get_dict())
    elif method == "low_any":
        aut = spot.translate(rec_f, "low", "any", dict=orig.get_dict())
    elif method == "trans_cls":
        t = spot.translator(orig.get_dict())
        t.set_type(spot.postprocessor.TGBA)
        t.set_pref(spot.postprocessor.Small)
        aut = t.run(rec_f)
    else:
        aut = spot.translate(rec_f, "Buchi", dict=orig.get_dict())
except Exception as e:
    print(f"PHASE translate ERROR {{time.monotonic()-t0:.2f}}s: "
          f"{{type(e).__name__}}: {{str(e)[:160]}}", flush=True)
    sys.exit(0)
print(f"PHASE translate ok {{time.monotonic()-t0:.2f}}s "
      f"states={{aut.num_states()}} edges={{aut.num_edges()}} "
      f"accsets={{aut.acc().num_sets()}}", flush=True)

t0 = time.monotonic()
try:
    eq = spot.are_equivalent(orig, aut)
except Exception as e:
    print(f"PHASE equiv ERROR {{time.monotonic()-t0:.2f}}s: "
          f"{{type(e).__name__}}: {{str(e)[:160]}}", flush=True)
    sys.exit(0)
print(f"PHASE equiv {{eq}} {{time.monotonic()-t0:.2f}}s", flush=True)
'''


def probe(fs: str, method: str) -> None:
    code = _CHILD.format(proj=PROJECT_ROOT, fs=fs, method=method)
    print(f"--- {fs!r} via {method} (budget {PROBE_TIMEOUT}s) ---")
    try:
        proc = subprocess.run([sys.executable, "-c", code],
                              capture_output=True, text=True,
                              timeout=PROBE_TIMEOUT, cwd=PROJECT_ROOT)
        out = (proc.stdout or "") + (proc.stderr or "")
        for line in out.splitlines():
            if line.startswith("PHASE") or "Error" in line:
                print("   ", line.strip())
        if proc.returncode not in (0,):
            print(f"    rc={proc.returncode}")
    except subprocess.TimeoutExpired as te:
        partial = (te.stdout or b"")
        if isinstance(partial, (bytes, bytearray)):
            partial = partial.decode("utf-8", errors="replace")
        last = [l for l in partial.splitlines() if l.startswith("PHASE")]
        print(f"    TIMEOUT >{PROBE_TIMEOUT}s; last completed phase: "
              f"{last[-1] if last else '(none — stuck before construct?)'}")


def main():
    cases = sys.argv[1:] or DEFAULT_CASES
    print(f"=== object-path translation probe (Couvreur fm vs translate) ===")
    for fs in cases:
        for method in METHODS:
            probe(fs, method)
    print("\nReading: 'fm'/'low_any' succeeding where 'default' times out or "
          "trips the acc-set limit means object-path verification is viable "
          "(TODO P0 item 3); all three failing means the wall is the tableau "
          "itself, not postprocessing.")


if __name__ == "__main__":
    main()
