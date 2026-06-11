#!/usr/bin/env python3
"""
kr/testing/trace_fin_semantics.py

Semantic grounding of every fin_c sub-term, per config, against ground-truth
automata built directly from the normalized D's semiautomaton (no LTL
involved), with containment direction + witness words (via ltl_diff).

For each reachable config C (state s = h^-1(C)):
  r_to   = iota ~> C                 GT: "run visits s at some time >= 0"
  r_gt0  = C >0~> C                  GT: "run STARTED AT s revisits s at time >= 1"
  r_with = iota ~> C(!(C>0~>C))      GT: "s visited at least once and finitely often"
  fin    = !(r_to) | r_with          GT: "s visited finitely often (possibly 0)"
  !fin                               GT: "s visited infinitely often"

Ground truths:
  - "visited i.o."    : copy semiautomaton, Buchi mark on out-edges of s.
  - "visited >= once" : seen-bit product (bit set at/after first visit),
                        Buchi marks on bit=1 edges (strict=: ignore time 0).
  - finite/compose    : spot.complement + spot.product.

This is the contradiction-milking tool for the Fin/R4 P0 work (GFa canary).

Run from project root:
    python3 kr/testing/trace_fin_semantics.py "GFa"
    python3 kr/testing/trace_fin_semantics.py "FGa" "G(a -> F b)"
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import spot

from kr import decompose_aut
import kr.reachability_operators as _ops
from kr.reachability_operators import (
    reach_strong,
    simplify_ltl,
)
from kr.fin import fin_c, _uncond_reach_strict
from ltl_diff import diff_report, to_aut


# ---------------------------------------------------------------- ground truth

def _copy_semiaut_buchi(D, mark_pred):
    """Copy D's semiautomaton; Buchi acceptance with Inf(0) marks exactly on
    edges where mark_pred(src, dst) holds."""
    g = spot.make_twa_graph(D.get_dict())
    g.copy_ap_of(D)
    g.set_buchi()
    g.new_states(D.num_states())
    g.set_init_state(D.get_init_state_number())
    for s in range(D.num_states()):
        for e in D.out(s):
            if mark_pred(s, e.dst):
                g.new_edge(s, e.dst, e.cond, [0])
            else:
                g.new_edge(s, e.dst, e.cond, [])
    return g


def gt_io(D, target):
    """GT automaton: run of D visits `target` infinitely often."""
    return _copy_semiaut_buchi(D, lambda s, d: s == target)


def gt_visited_once(D, init_state, target, strict: bool):
    """GT automaton: run of D *started at init_state* visits `target` at some
    time (>= 1 if strict, else >= 0). Seen-bit product: states (q, b),
    b sticky-set upon arriving at target; Buchi marks on b=1 edges
    (bit is sticky, so 'visited once' == 'bit set i.o.')."""
    n = D.num_states()
    g = spot.make_twa_graph(D.get_dict())
    g.copy_ap_of(D)
    g.set_buchi()
    g.new_states(2 * n)
    b0 = 1 if (not strict and init_state == target) else 0
    g.set_init_state(init_state + b0 * n)
    for q in range(n):
        for e in D.out(q):
            for b in (0, 1):
                nb = 1 if (b == 1 or e.dst == target) else 0
                g.new_edge(q + b * n, e.dst + nb * n, e.cond,
                           [0] if nb == 1 else [])
    return g


def gt_fin(D, target):
    """GT automaton: target visited finitely often (possibly zero)."""
    return spot.complement(gt_io(D, target))


def gt_once_and_fin(D, init_state, target):
    """GT automaton: target visited at least once AND finitely often."""
    return spot.product(gt_visited_once(D, init_state, target, strict=False),
                        gt_fin(D, target))


# ---------------------------------------------------------------- per-config

def check(name: str, gt_aut, produced_ltl: str) -> bool:
    """Compare GT automaton vs produced LTL string; print verdict; True if ok."""
    print(f"    {name} = {produced_ltl}")
    if produced_ltl.startswith(("ERROR", "NOT_IMPLEMENTED")):
        print(f"      SKIP ({produced_ltl})")
        return False
    rep = diff_report(gt_aut, produced_ltl, "GT", name)
    ok = "languages equivalent" in rep
    print(("      OK  " if ok else "      BAD ") + rep.strip())
    return ok


def trace_formula(formula_str: str) -> dict:
    print(f"\n================ {formula_str} ================")
    f = spot.formula(formula_str)
    casc = decompose_aut(f.translate())
    D = casc.original_aut
    init_state = D.get_init_state_number()
    init_cfg = casc.state_to_config.get(init_state)
    print(f"D: {D.num_states()} states, acc={D.get_acceptance()}, "
          f"init state {init_state} = config {init_cfg}")

    # mimic reconstruct's operator setup
    _ops._clear_casc_registry()
    _ops._register_casc(casc)
    if hasattr(_ops, "_lru_reach_strong"):
        _ops._lru_reach_strong.cache_clear()

    verdicts = {}
    for C in sorted(casc.reachable_configs()):
        s = casc.config_to_state.get(C)
        if s is None:
            continue
        print(f"\n  --- config C={C} (state {s})"
              f"{'  [== iota]' if C == init_cfg else ''} ---")

        r_to = simplify_ltl(reach_strong(init_cfg, None, "false", C, "true", casc))
        r_gt0 = simplify_ltl(_uncond_reach_strict(C, C, casc))
        no_ret = simplify_ltl(f"!({r_gt0})")
        r_with = simplify_ltl(reach_strong(init_cfg, None, "false", C, no_ret, casc))
        fin = simplify_ltl(fin_c(C, casc))
        notfin = simplify_ltl(f"!({fin})")

        v = {}
        v["r_to"] = check("r_to  (iota~>C, visit>=0)",
                          gt_visited_once(D, init_state, s, strict=False), r_to)
        v["r_gt0"] = check("r_gt0 (C>0~>C, revisit from C)",
                           gt_visited_once(D, s, s, strict=True), r_gt0)
        v["r_with"] = check("r_with (>=1 visit & finite)",
                            gt_once_and_fin(D, init_state, s), r_with)
        v["fin"] = check("fin   (finitely often)", gt_fin(D, s), fin)
        v["notfin"] = check("!fin  (infinitely often)", gt_io(D, s), notfin)
        verdicts[C] = v

    bad = [(C, k) for C, v in verdicts.items() for k, ok in v.items() if not ok]
    print(f"\n  SUMMARY {formula_str}: "
          f"{'ALL SUB-TERMS GROUNDED OK' if not bad else 'CONTRADICTIONS: ' + str(bad)}")
    return verdicts


def main():
    cases = sys.argv[1:] or ["GFa"]
    for fs in cases:
        trace_formula(fs)


if __name__ == "__main__":
    main()
