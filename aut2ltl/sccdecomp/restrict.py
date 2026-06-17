"""Accepting-SCC enumeration and the per-SCC mark restriction for sccdecomp.

`accepting_sccs` lists the accepting SCCs of an automaton (those whose internal
marks satisfy the acceptance condition). `restrict_marks(aut, C)` builds A↾C — a
copy keeping acceptance marks only on edges internal to C and dropping them
elsewhere — so its accepting runs are exactly those that lasso in C. See
algorithm.md.
"""

from typing import FrozenSet, List

import spot


def ensure_marked(aut: "spot.twa_graph") -> "spot.twa_graph":
    """The right form for the decomposition: acceptance must be mark-based, so an
    SCC with no marks reads as rejecting. An all-accepting automaton (no acceptance
    sets, the `t` condition) has nothing to clear — so add one Büchi set and mark
    every edge with it (acceptance `Inf(0)`). Language-preserving, since every
    infinite run already accepts. Automata that already carry marks are returned
    unchanged (marking an already-marked automaton would change its language)."""
    if aut.num_sets() > 0:
        return aut
    out = spot.make_twa_graph(aut.get_dict())
    out.copy_ap_of(aut)
    out.set_acceptance(1, "Inf(0)")
    for _ in range(aut.num_states()):
        out.new_state()
    full = spot.mark_t([0])
    for s in range(aut.num_states()):
        for e in aut.out(s):
            out.new_edge(s, e.dst, e.cond, full)
    out.set_init_state(aut.get_init_state_number())
    return out


def accepting_sccs(aut: "spot.twa_graph") -> List[FrozenSet[int]]:
    """The state sets of the accepting SCCs of `aut` — an SCC is accepting iff its
    internal marks satisfy the acceptance condition (spot's `is_accepting_scc`)."""
    si = spot.scc_info(aut)
    return [frozenset(int(s) for s in si.states_of(i))
            for i in range(si.scc_count()) if si.is_accepting_scc(i)]


def restrict_marks(aut: "spot.twa_graph", scc: FrozenSet[int]) -> "spot.twa_graph":
    """A copy of `aut` with acceptance marks kept only on edges internal to `scc`
    (both endpoints in `scc`) and cleared everywhere else — the automaton A↾C whose
    accepting runs are exactly those that lasso in `scc`. Structure, guards,
    acceptance condition, atomic propositions and init state are preserved."""
    out = spot.make_twa_graph(aut.get_dict())
    out.copy_ap_of(aut)
    out.set_acceptance(aut.acc())
    for _ in range(aut.num_states()):
        out.new_state()
    empty = spot.mark_t([])
    for s in range(aut.num_states()):
        for e in aut.out(s):
            keep = s in scc and e.dst in scc
            out.new_edge(s, e.dst, e.cond, e.acc if keep else empty)
    out.set_init_state(aut.get_init_state_number())
    return out
