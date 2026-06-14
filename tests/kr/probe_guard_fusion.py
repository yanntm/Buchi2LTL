#!/usr/bin/env python3
"""
kr/testing/probe_guard_fusion.py

Pre-implementation probe for the two user-proposed simplifications
(2026-06-12 session):

  1. Own LTL simplification rules — e.g. present-literal propagation
     `a & (!a | phi) -> a & phi` and guard factoring
     `(g1 & X t) | (g2 & X t) -> (g1|g2) & X t`.
     Question: does Spot's tl_simplifier (basics / full / our hybrid
     _simp_f) ALREADY do these, on the sizes where they occur?

  2. Letter fusion in the 2^AP expansion — at every enumeration site the
     disjunct/conjunct depends on the letter ONLY through its guard
     (structure is fixed by (pre, arr)), so letters with the same observed
     transition can be fused into one macro-letter with guard = OR of
     valuations, BDD-minimized (Minato ISOP via spot.bdd_to_formula).
     Question: how many distinct outcomes vs letters at the real sites
     (the fusion factor), and is the Spot BDD round-trip available?

Run from project root:
    python3 kr/testing/probe_guard_fusion.py
"""

import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr.ltl_builders import _simp_f, _get_tl_simp


def part_a_simplifier_rules():
    print("=== A. do existing simplifiers already do the two rules? ===")
    cases = [
        ("user ex.1: a & (!a | G(!a | Xa))   [== Ga]", "a & (!a | G(!a | Xa))"),
        ("user ex.2: (!a & Xa) | (a & Xa)    [== Xa]", "(!a & Xa) | (a & Xa)"),
        ("unit prop: a & (!a | F b)", "a & (!a | F b)"),
        ("factoring 3-way: (!a&!b&Xc)|(!a&b&Xc)|(a&b&Xc)", "(!a&!b&Xc)|(!a&b&Xc)|(a&b&Xc)"),
        ("factor distinct tails: (a&Xc)|(!a&Xd)", "(a & Xc) | (!a & Xd)"),
    ]
    for label, s in cases:
        f = spot.formula(s)
        full = _get_tl_simp(True).simplify(f)
        basic = _get_tl_simp(False).simplify(f)
        print(f"  {label}")
        print(f"    full  : {full}")
        print(f"    basics: {basic}")


def part_b_real_outputs():
    print("\n=== B. real small-case outputs, then one full-simp on the WHOLE output ===")
    from aut2ltl.kr import decompose_aut
    from aut2ltl.kr.reachability import reconstruct_ltl_paper_style
    for case in ["Ga", "Xa", "Fa"]:
        f = spot.formula(case)
        casc = decompose_aut(f.translate())
        res = reconstruct_ltl_paper_style(casc)
        whole = _get_tl_simp(True).simplify(res)
        print(f"  case '{case}':")
        print(f"    pipeline output : {res}")
        print(f"    full-simp(whole): {whole}")


def part_c_collision_census():
    print("\n=== C. letter-outcome collision census per enumeration site ===")
    print("  (per level, per pre-config: #letters with non-false guard vs")
    print("   #distinct arrival configs == the fusion factor at that site)")
    from aut2ltl.kr import decompose_aut
    from aut2ltl.kr.reachability import reconstruct_ltl_paper_style  # noqa: F401 (import parity)
    for case in ["Xa", "X X a", "G(a -> Xb)", "G(p -> (q U r))"]:
        f = spot.formula(case)
        casc = decompose_aut(f.translate())
        n_letters = casc.num_letters()
        print(f"  case '{case}': {casc.num_levels} levels, {n_letters} letters, "
              f"{len(casc.all_configs())} configs")
        # global fusion: letters identical on EVERY config
        action = {}
        for li in range(n_letters):
            sig = []
            for pre in casc.all_configs():
                try:
                    sig.append(casc.move_config(pre, li))
                except Exception:
                    sig.append(None)
            action[li] = tuple(sig)
        n_global = len(set(action.values()))
        print(f"    global action classes: {n_global} / {n_letters} letters")
        # site-local fusion: per (level, pre), group letters by arrival
        for level in range(casc.num_levels):
            ratios = []
            for pre in casc.all_configs():
                if len(pre) <= level:
                    continue
                groups = defaultdict(int)
                for li in range(n_letters):
                    try:
                        arr = casc.move_config(pre, li)
                    except Exception:
                        continue
                    groups[arr] += 1
                if groups:
                    ratios.append((sum(groups.values()), len(groups)))
            tot_l = sum(r[0] for r in ratios)
            tot_g = sum(r[1] for r in ratios)
            print(f"    level {level}: {tot_l} (letter,pre) pairs -> {tot_g} "
                  f"(outcome,pre) groups  (fusion x{tot_l / max(tot_g, 1):.2f})")


def part_d_bdd_roundtrip():
    print("\n=== D. Spot BDD round-trip for guard minimization (Minato ISOP) ===")
    has_f2b = hasattr(spot, "formula_to_bdd")
    has_b2f = hasattr(spot, "bdd_to_formula")
    print(f"  spot.formula_to_bdd available: {has_f2b}")
    print(f"  spot.bdd_to_formula available: {has_b2f}")
    if not (has_f2b and has_b2f):
        print("  -> need the aut-based fallback (translate guard, read edge conds)")
        return
    d = spot.make_bdd_dict()
    owner = spot.make_twa_graph(d)  # bindings: owner must be a twa_graph
    tests = [
        "(!a & Xa) | (a & Xa)",  # temporal: NOT a guard - expect failure or X-handling
        "(!a & !b) | (!a & b) | (a & b)",
        "(!a & !b) | (a & !b)",
        "(a & b) | (!a & !b)",
    ]
    for s in tests:
        f = spot.formula(s)
        try:
            b = spot.formula_to_bdd(f, d, owner)
            g = spot.bdd_to_formula(b, d)
            print(f"  {s}  ->  {g}", flush=True)
        except Exception as e:
            print(f"  {s}  ->  EXC {type(e).__name__}: {e}", flush=True)


if __name__ == "__main__":
    part_a_simplifier_rules()
    part_d_bdd_roundtrip()
    part_b_real_outputs()
    part_c_collision_census()
