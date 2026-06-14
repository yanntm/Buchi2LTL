#!/usr/bin/env python3
"""
kr/testing/probe_muller_overlap.py

One-shot: is the Muller-DNF assembly the census driver? For a reconstructed
formula whose root is an Or of per-Muller-set disjuncts, report per-disjunct
DAG size / census and the pairwise census OVERLAP (H2: disjoint census means
the DNF multiplies the obligation web; shared census means it does not), and
attempt bounded language containment between disjuncts (H3: a subsumed
disjunct would make the root Or itself redundant) — translation may hit the
32-acc cap; that outcome is reported, not fatal.

Run from project root:
    python3 kr/testing/probe_muller_overlap.py "G(p -> (q U r))"
"""

import signal
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr import decompose_aut
from aut2ltl.kr.reachability import reconstruct_ltl_paper_style

TEMPORAL_KINDS = ("U", "M", "R", "W", "F", "G")


def census(f):
    seen, stack, out = set(), [f], set()
    while stack:
        g = stack.pop()
        if g in seen:
            continue
        seen.add(g)
        if g.kindstr() in TEMPORAL_KINDS:
            out.add(g)
        stack.extend(g)
    return out, len(seen)


def bounded(fn, seconds=10):
    def handler(signum, frame):
        raise TimeoutError
    old = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        return fn()
    except TimeoutError:
        return "TIMEOUT"
    except Exception as e:
        return f"ERR:{str(e)[:60]}"
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def main():
    formula_str = sys.argv[1] if len(sys.argv) > 1 else "G(p -> (q U r))"
    f = spot.formula(formula_str)
    casc = decompose_aut(f.translate())
    root = reconstruct_ltl_paper_style(casc)
    print(f"=== Muller-disjunct overlap for '{formula_str}' ===")
    if not root._is(spot.op_Or):
        print(f"root is {root.kindstr()}, not Or — single disjunct, nothing to compare")
        return
    disjuncts = list(root)
    censuses = []
    for i, d in enumerate(disjuncts):
        c, dag = census(d)
        censuses.append(c)
        print(f"  disjunct {i}: DAG={dag} census={len(c)}", flush=True)
    whole, _ = census(root)
    print(f"  whole root census: {len(whole)}", flush=True)
    for i in range(len(disjuncts)):
        for j in range(i + 1, len(disjuncts)):
            inter = censuses[i] & censuses[j]
            print(f"  census overlap d{i} ∩ d{j}: {len(inter)} "
                  f"(jaccard {len(inter)/max(1,len(censuses[i]|censuses[j])):.2f})",
                  flush=True)

    # one level deeper: which conjunct of a disjunct carries the census?
    for i, d in enumerate(disjuncts):
        if not d._is(spot.op_And):
            continue
        print(f"\n  disjunct {i} conjuncts (census per ¬Fin/Fin/reach term):",
              flush=True)
        seen_c = set()
        for k, conj in enumerate(d):
            c, dag = census(conj)
            fresh = c - seen_c
            seen_c |= c
            print(f"    conj {k}: head={conj.kindstr():3} DAG={dag:5} "
                  f"census={len(c):3} new={len(fresh):3}  {str(conj)[:60]}",
                  flush=True)

    if "--contain" not in sys.argv:
        return  # translation guaranteed over the acc cap for big censuses;
                # opt-in only (and NB: native Spot calls ignore SIGALRM)
    print("\nbounded containment (10s each; acc-cap/timeout reported):", flush=True)
    auts = []
    for i, d in enumerate(disjuncts):
        a = bounded(lambda d=d: spot.translate(d, "small", "low"))
        auts.append(a)
        desc = a if isinstance(a, str) else f"{a.num_states()} states"
        print(f"  translate d{i}: {desc}")
    for i in range(len(disjuncts)):
        for j in range(len(disjuncts)):
            if i == j or isinstance(auts[i], str) or isinstance(auts[j], str):
                continue
            r = bounded(lambda i=i, j=j: spot.contains(auts[j], auts[i]))
            print(f"  L(d{i}) ⊆ L(d{j}) : {r}")


if __name__ == "__main__":
    main()
