"""Probe: is the DETERMINISTIC anchored read-off exact for a rejecting star?

Tests the idea (idea 1's sound half + the cut-copy exit + the q0 anchor): when
the SCC's L-partition is deterministic (phase = last letter, partscc's
precondition), emit a FLAT, fixpoint-free candidate

    cand = O(h)  ∧  ( exit_at_0  ∨  ( law  U  exit_after_entry ) )

    law              = ⋀_{p∈C} ( L(p) → X O(p) )            -- transition law
    exit_after_entry = ⋁_{p, exit p→dst} ( L(p) ∧ X(γ ∧ X φ_dst) )
    exit_at_0        = ⋁_{hub exit h→dst}  ( γ ∧ X φ_dst )   -- the position-0 hub case

with L(p)=⋁ guards entering p (within C), O(p)=⋁ all out-guards of p, φ_dst the
child label of an exit target (a cut-copy daisy / true sink). The q0 anchor O(h)
plus the per-revisit law is what the flat LEAVE lacked — it should reject the
daisystar_loose witness and be language-equivalent where the L-partition is
deterministic.

Usage:  python3 tests/daisystardet/probe_det.py '<LTL>' | <path-to.hoa>
Reports: the partition, whether L is a deterministic partition, the candidate,
and the Spot equivalence verdict with a containment witness each way.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import spot                                                  # noqa: E402
import buddy                                                 # noqa: E402

from aut2ltl.language import Language                        # noqa: E402
from aut2ltl.result import decline                           # noqa: E402
from aut2ltl.daisy.daisy import Daisy                        # noqa: E402
from aut2ltl.daisystardet.shape import init_scc_states, reroot  # noqa: E402

_F = spot.formula


def _or(fs):
    return _F.Or(fs) if fs else _F.ff()


def _and(fs):
    return _F.And(fs) if fs else _F.tt()


def main(arg: str) -> None:
    lang = Language.of(spot.automaton(arg)) if os.path.exists(arg) else Language.of_ltl(arg)
    aut = lang.tgba()
    h = aut.get_init_state_number()
    si = spot.scc_info(aut)
    d = aut.get_dict()

    def f(bdd):
        return spot.bdd_to_formula(bdd, d)

    rej = si.is_rejecting_scc(si.scc_of(h))
    C = init_scc_states(aut, h)
    print(f"input      : {arg}")
    print(f"init SCC    : states={sorted(C)} rejecting={rej}")

    # Per-state L (incoming guards within C), O (all out-guards), and exits.
    L = {p: buddy.bddfalse for p in C}
    O = {p: buddy.bddfalse for p in C}
    exits = {p: [] for p in C}          # p -> [(guard_bdd, dst)]
    for src in C:
        for e in aut.out(src):
            O[src] = O[src] | e.cond
            if e.dst in C:
                L[e.dst] = L[e.dst] | e.cond
            else:
                exits[src].append((e.cond, e.dst))

    # Deterministic L-partition? (each tight, pairwise disjoint)
    states = sorted(C)
    det = True
    for p in states:
        if L[p] == buddy.bddtrue or (L[p] == buddy.bddfalse and p != h):
            det = False
    for i in range(len(states)):
        for j in range(i + 1, len(states)):
            if (L[states[i]] & L[states[j]]) != buddy.bddfalse:
                det = False
    print(f"L-partition : deterministic={det}")
    for p in states:
        ex = [(str(f(g)), dst) for g, dst in exits[p]]
        print(f"  state {p}: L={f(L[p])}  O={f(O[p])}  exits={ex}")

    # Children for exit targets (a declining-floor daisy labels a trivial sink as T).
    child = Daisy(decline)
    phi = {}
    for p in C:
        for g, dst in exits[p]:
            if dst not in phi:
                phi[dst] = child(Language.of(reroot(aut, dst))).formula

    # Build the deterministic anchored candidate.
    law = _and([_F.Or([_F.Not(f(L[p])), _F.X(f(O[p]))]) for p in states])
    after = []
    for p in states:
        for g, dst in exits[p]:
            after.append(_F.And([f(L[p]), _F.X(_F.And([f(g), _F.X(phi[dst])]))]))
    exit_after_entry = _or(after)
    exit_at_0 = _or([_F.And([f(g), _F.X(phi[dst])]) for g, dst in exits[h]])
    cand = _F.And([f(O[h]), _F.Or([exit_at_0, _F.U(law, exit_after_entry)])])
    print(f"candidate  : {cand}")

    # Spot equivalence verdict.
    try:
        ca = cand.translate("GeneralizedBuchi", "Small", "High")
        equiv = spot.are_equivalent(aut, ca)
        print(f"EQUIVALENT : {equiv}")
        if not equiv:
            loose = ca.intersecting_word(spot.complement(aut))
            tight = aut.intersecting_word(spot.complement(ca))
            print(f"  too loose (cand\\input): {loose}")
            print(f"  too tight (input\\cand): {tight}")
    except Exception as e:
        print(f"  (verdict failed: {e})")


if __name__ == "__main__":
    main(sys.argv[1])
