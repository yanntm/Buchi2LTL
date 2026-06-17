"""The `fuse2` size-2 SCC over-approximation rewrite (see algorithm.md).

`fuse2(aut)` is a gated TGBA→TGBA rewriting, not a translator. It finds the first
non-accepting strongly-connected component of exactly two states, unfolds that cycle
once while over-approximating the residual self-loop to `true`, and returns the
result ONLY when a Spot equivalence test confirms the language was preserved. The
rewrite alone is a deliberate over-approximation (potentially unsound); the gate is
what makes `fuse2` safe to use. The product has only self-loop cycles, so `daisy`
can label it where it could not label the original two-state cycle.
"""

from __future__ import annotations

from typing import List, Optional, Set, Tuple

import spot
import buddy

_SCC_SIZE = 2


def _size2_nonacc_scc(si: "spot.scc_info") -> Optional[List[int]]:
    """The two states of the first non-accepting SCC of size exactly two, or None."""
    for scc in range(si.scc_count()):
        if si.is_accepting_scc(scc):
            continue
        states = list(si.states_of(scc))
        if len(states) == _SCC_SIZE:
            return states
    return None


def _exits_to_accepting(
    aut: "spot.twa_graph", si: "spot.scc_info", state: int, scc: Set[int]
) -> bool:
    """True iff `state` has an edge leaving its SCC into an accepting SCC."""
    return any(
        e.dst not in scc and si.is_accepting_scc(si.scc_of(e.dst))
        for e in aut.out(state)
    )


def _roles(
    aut: "spot.twa_graph", si: "spot.scc_info", states: List[int]
) -> Optional[Tuple[int, int]]:
    """Assign (initiator, satellite): the unique state with an accepting exit is the
    initiator, the other the satellite. None when both or neither exit to accepting
    (the shape is ambiguous / has no productive exit — not ours)."""
    a, b = states
    pair = {a, b}
    exit_a = _exits_to_accepting(aut, si, a, pair)
    exit_b = _exits_to_accepting(aut, si, b, pair)
    if exit_a == exit_b:
        return None
    return (a, b) if exit_a else (b, a)


def _unfold(
    aut: "spot.twa_graph", initiator: int, satellite: int
) -> "spot.twa_graph":
    """Build the over-approximated rewrite A' (algorithm.md, steps 1–4). Pure
    construction — soundness is the caller's gate, not asserted here."""
    pair = {initiator, satellite}
    out = spot.make_twa_graph(aut.get_dict())
    out.copy_ap_of(aut)
    out.set_acceptance(aut.acc())
    smap = {s: out.new_state() for s in range(aut.num_states())}

    # 1. Copy every edge, except drop the cycle's internal back-edges — keeping only
    #    the first loop step initiator -> satellite.
    for src in range(aut.num_states()):
        for e in aut.out(src):
            internal = src in pair and e.dst in pair
            if internal and not (src == initiator and e.dst == satellite):
                continue
            out.new_edge(smap[src], smap[e.dst], e.cond, e.acc)

    # 2. Splice the unfolded initiator copy p': every initiator edge but p -> q (its
    #    accepting exits, and its self-loop if any, now leaving p').
    prime = out.new_state()
    for e in aut.out(initiator):
        if e.dst != satellite:
            out.new_edge(prime, smap[e.dst], e.cond, e.acc)

    # 3. Redirect the satellite's return edge q -> p to q -> p'.
    for e in aut.out(satellite):
        if e.dst == initiator:
            out.new_edge(smap[satellite], prime, e.cond, e.acc)

    # 4. Over-approximate the dwell: the satellite self-loop guard becomes true.
    for e in aut.out(satellite):
        if e.dst == satellite:
            out.new_edge(smap[satellite], smap[satellite], buddy.bddtrue, e.acc)
            break

    out.set_init_state(smap[aut.get_init_state_number()])
    return out


def fuse2(aut: "spot.twa_graph") -> Optional["spot.twa_graph"]:
    """Gated size-2 over-approximation rewrite (see algorithm.md).

    Returns an equivalent self-loop-only automaton when the shape matches and the
    language is preserved, else None (no match, or the over-approximation changed the
    language). Never returns a non-equivalent automaton."""
    si = spot.scc_info(aut)
    states = _size2_nonacc_scc(si)
    if states is None:
        return None
    roles = _roles(aut, si, states)
    if roles is None:
        return None
    rewritten = _unfold(aut, roles[0], roles[1])
    try:
        return rewritten if spot.are_equivalent(aut, rewritten) else None
    except Exception:
        return None


__all__ = ["fuse2"]
