#!/usr/bin/env python3
"""
kr/testing/probe_tail_anatomy.py

Anatomy of the subproblem explosion on (a & X a)-style cases: after building
the formula, dissect the helper memo (_helper_memo: one entry per DISTINCT
(helper, S, B, beta, T, tau, level) subproblem) and report, per level:

  - subproblem count by helper tag (ss/ss0/ws/ws0/dc)
  - DISTINCT tau tails and DISTINCT beta guards (the tail-wrapping axis:
    tau -> sigma & X tau multiplies one variant per candidate letter)
  - distinct (S,B,T) config triples (the avoid-conjunct axis)
  - tau tree-size quartiles (how deep the wrapped tails have grown)

This separates the three suspected multipliers (tail wrapping, avoid
conjuncts, Fin fan-out) on a per-level basis: the level where #tau jumps is
where wrapping compounds; #(S,B,T) jumping instead blames the avoid web.

Run from project root (small cases only — build must fit the budget):
    python3 kr/testing/probe_tail_anatomy.py "a & X a"
    python3 kr/testing/probe_tail_anatomy.py "X(a & X a)"
"""

import sys
import time
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr import decompose_aut
import aut2ltl.kr.reachability_operators as _ops
from aut2ltl.kr.ltl_builders import _tree_size_f
from aut2ltl.kr.reachability import reconstruct_ltl_paper_style


def quartiles(xs):
    if not xs:
        return (0, 0, 0)
    s = sorted(xs)
    return (s[0], s[len(s) // 2], s[-1])


def main():
    fs = sys.argv[1] if len(sys.argv) > 1 else "a & X a"
    print(f"=== tail anatomy for '{fs}' ===")
    f = spot.formula(fs)
    casc = decompose_aut(f.translate())
    print(f"cascade: {casc.num_levels} levels, sizes={[l.size for l in casc.levels]}, "
          f"letters={casc.num_letters()}")

    t0 = time.monotonic()
    res_f = reconstruct_ltl_paper_style(casc)
    print(f"build: {time.monotonic()-t0:.2f}s, "
          f"distinct reach subproblems={_ops.PAPER_REACH_CALLS}, "
          f"helper memo entries={len(_ops._helper_memo)}")

    # helper memo key: (tag, cid, S, B, beta_f, T, tau_f, level)
    by_level_tag = defaultdict(int)
    taus = defaultdict(set)      # level -> distinct tau ids
    betas = defaultdict(set)     # level -> distinct beta ids
    sbt = defaultdict(set)       # level -> distinct (S,B,T)
    tau_sizes = defaultdict(list)
    tau_objs = {}
    for key in _ops._helper_memo:
        tag, _cid, S, B, beta_f, T, tau_f, level = key
        by_level_tag[(level, tag)] += 1
        if tau_f.id() not in taus[level]:
            tau_sizes[level].append(_tree_size_f(tau_f))
        taus[level].add(tau_f.id())
        tau_objs[tau_f.id()] = tau_f
        betas[level].add(beta_f.id())
        sbt[level].add((S, B, T))

    levels = sorted({lv for (lv, _t) in by_level_tag})
    tags = ["ss", "ss0", "ws", "ws0", "dc"]
    print(f"\n{'lvl':>3} " + "".join(f"{t:>7}" for t in tags)
          + f" {'#tau':>6} {'#beta':>6} {'#SBT':>6}  tau-size min/med/max")
    for lv in levels:
        row = "".join(f"{by_level_tag.get((lv, t), 0):>7}" for t in tags)
        q = quartiles(tau_sizes[lv])
        print(f"{lv:>3} {row} {len(taus[lv]):>6} {len(betas[lv]):>6} "
              f"{len(sbt[lv]):>6}  {q[0]}/{q[1]}/{q[2]}")

    # The multiplication law: distinct tails per level vs configs-and-letters.
    # If #tau(level+1) ~ #tau(level) x #stay-letters, wrapping is the driver.
    print("\ntau growth ratios (level -> level+1):")
    for a, b in zip(levels, levels[1:]):
        na, nb = len(taus[a]), len(taus[b])
        if na:
            print(f"  L{a} -> L{b}: {na} -> {nb}  (x{nb/na:.1f})")

    # Sample a few deepest-level tails to eyeball the wrapped shape.
    if levels:
        deep = levels[-1]
        sample = sorted(taus[deep])[:4]
        print(f"\nsample tails at level {deep} (truncated):")
        for tid in sample:
            s = str(tau_objs[tid])
            print("   ", s[:110] + ("..." if len(s) > 110 else ""))


if __name__ == "__main__":
    main()
