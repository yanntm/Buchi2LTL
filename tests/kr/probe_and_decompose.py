#!/usr/bin/env python3
"""kr/testing/probe_and_decompose.py — AND-by-acceptance-set decomposition probe.

Tests the P1 dual of strength decomposition: for a DETERMINISTIC automaton with
conjunctive acceptance (generalized Büchi  Inf(0)&Inf(1)&… / Streett), split the
acceptance condition by top_conjuncts(), run the EXISTING kr on each single-set
piece, and recombine with a root AND. Soundness: determinism makes
L(A,⋀cᵢ)=⋂L(A,cᵢ) exact (shared run).

For each formula, reports:
  - monolithic kr: DAG nodes / distinct-temporals / tree (capped)
  - per-piece kr:  same, per conjunct
  - recombined ⋀ : same, plus Spot equivalence vs the original (budgeted)

Run from project root:
    python3 kr/testing/probe_and_decompose.py
    python3 kr/testing/probe_and_decompose.py "GFa & GFb" "GFa & GFb & GFc"
"""
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot
from aut2ltl.kr import decompose_aut, reconstruct_ltl_paper_style
from aut2ltl.kr.ltl_builders import _tree_size_f

TREE_CAP = 50_000_000
EQUIV_TIMEOUT = int(os.environ.get("KR_SPOT_EQUIV_TIMEOUT", "10"))


def dag_nodes(f):
    seen, stack = set(), [f]
    while stack:
        g = stack.pop()
        if g.id() in seen:
            continue
        seen.add(g.id())
        stack.extend(g)
    return len(seen)


def distinct_temporals(f):
    seen, stack, n = set(), [f], 0
    while stack:
        g = stack.pop()
        if g.id() in seen:
            continue
        seen.add(g.id())
        if g.kindstr() in ("U", "M", "R", "W", "F", "G"):
            n += 1
        stack.extend(g)
    return n


def measure(tag, f):
    nt = _tree_size_f(f) if f is not None else 0
    print(f"    {tag:18s} DAG={dag_nodes(f):>7d}  temporals={distinct_temporals(f):>5d}  "
          f"tree={nt:>12d}{' (capped)' if nt >= TREE_CAP else ''}")
    return nt


def kr_of(aut):
    """decompose_aut + reconstruct on a Spot automaton -> formula DAG."""
    casc = decompose_aut(aut)
    return reconstruct_ltl_paper_style(casc)


def acc_split_pieces(aut):
    """Yield (label, sub-automaton) per top-level acceptance conjunct."""
    conj = aut.acc().get_acceptance().top_conjuncts()
    pieces = []
    for i, c in enumerate(conj):
        sub = spot.automaton(aut.to_str("hoa"))  # independent clone (HOA round-trip)
        sub.set_acceptance(spot.acc_cond(aut.num_sets(), c))
        spot.cleanup_acceptance_here(sub)
        pieces.append((f"piece[{i}] {c}", sub))
    return pieces


_EQUIV_CHILD = '''
import sys, json, spot
p = json.load(sys.stdin)
A = spot.formula(p["orig"]).translate("Buchi")
B = spot.formula(p["rec"])
if p["rec"] not in ("true","false"):
    B = B.translate("Buchi")
print("EQ:" + str(bool(spot.are_equivalent(A, B))))
'''


def equiv(orig_str, rec_f):
    import json
    rec = str(rec_f)
    try:
        proc = subprocess.run([sys.executable, "-c", _EQUIV_CHILD],
                              input=json.dumps({"orig": orig_str, "rec": rec}),
                              capture_output=True, text=True,
                              timeout=EQUIV_TIMEOUT, cwd=PROJECT_ROOT)
    except subprocess.TimeoutExpired:
        return f"SPOT_TIMEOUT >{EQUIV_TIMEOUT}s"
    out = (proc.stdout or "") + (proc.stderr or "")
    for line in out.splitlines():
        if line.strip().startswith("EQ:"):
            return line.strip()[3:]
    return "err:no-output"


# Compositional check: kr(pieceᵢ) vs the SUB-AUTOMATON it was built from.
# Each piece is single-Büchi (small) so this stays well under the 32-acc cap
# even when the recombined ⋀ does not. Sound recombination then follows from
# L(A)=⋂L(pieceᵢ): if every piece formula matches its sub-automaton language,
# ⋀ kr(pieceᵢ) ≡ L(A) without ever translating the product.
_EQUIV_AUT_CHILD = '''
import sys, json, spot
p = json.load(sys.stdin)
A = spot.automaton(p["hoa"]).translate("Buchi") if False else spot.automaton(p["hoa"])
B = spot.formula(p["rec"])
if p["rec"] not in ("true","false"):
    B = B.translate("Buchi")
print("EQ:" + str(bool(spot.are_equivalent(A, B))))
'''


def equiv_piece(sub_aut, rec_f):
    import json
    try:
        proc = subprocess.run([sys.executable, "-c", _EQUIV_AUT_CHILD],
                              input=json.dumps({"hoa": sub_aut.to_str("hoa"),
                                                "rec": str(rec_f)}),
                              capture_output=True, text=True,
                              timeout=EQUIV_TIMEOUT, cwd=PROJECT_ROOT)
    except subprocess.TimeoutExpired:
        return f"SPOT_TIMEOUT >{EQUIV_TIMEOUT}s"
    out = (proc.stdout or "") + (proc.stderr or "")
    for line in out.splitlines():
        if line.strip().startswith("EQ:"):
            return line.strip()[3:]
    return "err:no-output"


SKIP_MONO = os.environ.get("KR_SKIP_MONO", "0") == "1"


def run_case(fs):
    print(f"=== {fs} ===", flush=True)
    f = spot.formula(fs)
    aut = spot.translate(f, "deterministic", "generic")
    print(f"  det aut: acc={aut.acc()} states={aut.num_states()}", flush=True)

    # --- AND-decomposed (the part under test — run + print FIRST) ---
    pieces = acc_split_pieces(aut)
    if len(pieces) < 2:
        print("  (acceptance is not a top-level conjunction; no AND split)", flush=True)
    else:
        t0 = time.monotonic()
        piece_fs = []
        print(f"  decomposed into {len(pieces)} pieces:", flush=True)
        all_pieces_ok = True
        for label, sub in pieces:
            pf = kr_of(sub)
            piece_fs.append(pf)
            measure(label, pf)
            eqp = equiv_piece(sub, pf)
            print(f"      kr(piece) == sub-automaton? {eqp}", flush=True)
            all_pieces_ok = all_pieces_ok and (eqp == "True")
        recombined = spot.formula.And(piece_fs)
        print(f"  recombined ⋀ ({time.monotonic()-t0:.2f}s):", flush=True)
        measure("recombined", recombined)
        print(f"  compositional verdict (all pieces ok => ⋀ ≡ L(A)): "
              f"{'SOUND' if all_pieces_ok else 'INCOMPLETE'}", flush=True)
        print(f"  direct equiv(recombined, {fs})? {equiv(fs, recombined)}", flush=True)

    # --- monolithic baseline LAST (often blows the guard/budget — that IS the
    #     finding; KR_SKIP_MONO=1 to skip a known blowup and stay under 15s). ---
    if SKIP_MONO:
        print("  monolithic kr: SKIPPED (KR_SKIP_MONO=1)", flush=True)
    else:
        t0 = time.monotonic()
        try:
            mono = kr_of(spot.translate(f))
            print(f"  monolithic kr ({time.monotonic()-t0:.2f}s):", flush=True)
            measure("monolithic", mono)
        except Exception as e:
            print(f"  monolithic kr ({time.monotonic()-t0:.2f}s): BLEW UP -> {str(e)[:90]}", flush=True)
    print(flush=True)


def main():
    cases = sys.argv[1:] or ["GFa & GFb", "GFa & GFb & GFc", "GFa & Gb"]
    for fs in cases:
        try:
            run_case(fs)
        except Exception as e:
            import traceback
            print(f"  ERROR: {repr(e)}")
            traceback.print_exc()
            print()


if __name__ == "__main__":
    main()
