#!/usr/bin/env python3
"""
tests/sl/trace_sl_driven.py — trace SlDriven's full-suffix delegation on one HOA.

Reproduces the `--use sl_driven,str` path (SlDriven over the kr cascade) on an
automaton FILE, wrapping the scc_labeler so each delegated sub-automaton is
printed: which original state q it is rooted at, the states reachable from q
(the "suffix"), and the formula the delegate returned. Reveals when the suffix
loops back onto earlier states (the unsound case that yields e.g. `a`).

Usage:
    python3 tests/sl/trace_sl_driven.py <hoa-file>
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.language import Language
from aut2ltl.bls.aut2cas import as_translator
from aut2ltl.bls.hierarchy_class import make_hierarchy_class
from aut2ltl.sl.reconstruction import reconstruct_ltl
from aut2ltl.sl.reconstruction_helpers import _sub_automaton_from


def _reachable(aut: "spot.twa_graph", src: int) -> set:
    seen, stack = {src}, [src]
    while stack:
        s = stack.pop()
        for e in aut.out(s):
            if e.dst not in seen:
                seen.add(e.dst)
                stack.append(e.dst)
    return seen


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return 2
    aut = spot.automaton(sys.argv[1])
    lang = Language.of(aut)
    tgba = lang.tgba()
    print(f"tgba: {tgba.num_states()} states, init={tgba.get_init_state_number()}")
    si = spot.scc_info(tgba)
    for s in range(si.scc_count()):
        members = [int(x) for x in si.states_of(s)]
        print(f"  SCC {s}: states={members} size={len(members)}")

    # Pre-map each original state to its reachable set, to identify a delegated
    # sub (whose states are renumbered after purge) by reachable-set size.
    reach = {q: _reachable(tgba, q) for q in range(tgba.num_states())}
    print("tgba HOA:")
    print(tgba.to_str("hoa"))
    print(f"reachable sets: {{q: sorted(R)}} = "
          + str({q: sorted(R) for q, R in reach.items()}))

    # Show what _apply_downstream_invariants strips: per-state invariant literals
    # and the resulting (stripped) edge labels handed to delegation.
    from aut2ltl.sl.reconstruction_helpers import (
        _compute_state_invariants, _apply_downstream_invariants)
    inv = _compute_state_invariants(tgba)
    print(f"state invariants (literals): {dict(inv)}")
    stripped = _apply_downstream_invariants(spot.automaton(tgba.to_str('hoa')), inv)
    sd = stripped.get_dict()
    print("stripped edges:")
    for s in range(stripped.num_states()):
        for e in stripped.out(s):
            print(f"  {e.src} -[{spot.bdd_to_formula(e.cond, sd)}]-> {e.dst}"
                  f"  acc={list(e.acc.sets())}")

    cascade = as_translator(make_hierarchy_class(None))

    # Intercept _sub_automaton_from in the reconstruction namespace to record the
    # actual q each delegation is rooted at (and on which — possibly modified —
    # automaton), since reconstruct_ltl delegates from an invariant-injected aut.
    import aut2ltl.sl.reconstruction as _recon
    _orig_sub = _recon._sub_automaton_from
    _last = {}

    def _spy_sub(a, q):
        sub = _orig_sub(a, q)
        _last["q"] = q
        _last["reach_in_aut"] = sorted(_reachable(a, q))
        return sub
    _recon._sub_automaton_from = _spy_sub

    def labeler(sub):
        r = cascade(Language.of(sub))
        frag = None if (r.declined or r.formula is None) else r.formula
        # Truncate: a delegated core can be a multi-MB formula; print size + head.
        fs = "None" if frag is None else f"[{frag.size()} nodes] {str(frag)[:70]}"
        print(f"  DELEGATE q={_last.get('q')}: sub={sub.num_states()} states "
              f"reach-in-aut={_last.get('reach_in_aut')}  -> {fs}")
        return frag

    out = reconstruct_ltl(tgba, scc_labeler=labeler)
    res = out.formula
    rs = "None" if res is None else f"[{res.size()} nodes] {str(res)[:70]}"
    print(f"RESULT: declined={out.declined} formula={rs}")

    # Language proof of the mechanism: compare the suffix-from-0 of the PRISTINE
    # vs the STRIPPED automaton against the produced `a`. Tiny automata, cheap.
    from tests.kr.ltl_diff import diff_report
    pristine0 = _orig_sub(tgba, 0)
    stripped0 = _orig_sub(stripped, 0)
    print("\nL(pristine sub-from-0)  vs  a:")
    print(diff_report(pristine0, "a", "L_true", "a"))
    print("L(stripped sub-from-0)  vs  a:")
    print(diff_report(stripped0, "a", "L_stripped", "a"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
