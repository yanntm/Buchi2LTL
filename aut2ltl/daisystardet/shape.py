"""Structure helpers behind the daisystardet reachability read-off.

daisystardet peels a *rejecting* SCC whose entry-letter partition is
deterministic. These helpers detect that precondition and expose the per-state
guard data the read-off consumes:

* `init_scc_states` — the states of the initial SCC `C` daisystardet peels.
* `scc_data` — per-state `L` (⋁ guards entering the state within `C`), `O` (⋁ all
  out-guards) and `exits` (`state → [(guard, dst∉C)]`), in one edge pass.
* `is_deterministic` — `partscc`'s input-determinizing test on the `L`-partition.

`reroot` (the `A↓dst` rebase for an exit child) is reused verbatim from
`aut2ltl.daisy.shape`.
"""

from typing import Dict, List, Set, Tuple

import spot
import buddy

from aut2ltl.daisy.shape import reroot  # reused verbatim: A↓dst for exit delegation

__all__ = ["init_scc_states", "scc_data", "is_deterministic", "reroot"]


def init_scc_states(aut: "spot.twa_graph", h: int) -> Set[int]:
    """The states of the SCC containing the initial state `h` — the component `C`
    daisystardet peels."""
    si = spot.scc_info(aut)
    return {int(s) for s in si.states_of(si.scc_of(h))}


def scc_data(
    aut: "spot.twa_graph", C: Set[int], h: int
) -> Tuple[Dict[int, "buddy.bdd"], Dict[int, "buddy.bdd"],
          Dict[int, List[Tuple["buddy.bdd", int]]]]:
    """Per-state `L` (⋁ guards entering the state within `C`), `O` (⋁ all
    out-guards) and `exits` (`state → [(guard, dst∉C)]`), in one edge pass."""
    L = {p: buddy.bddfalse for p in C}
    O = {p: buddy.bddfalse for p in C}
    exits: Dict[int, List[Tuple["buddy.bdd", int]]] = {p: [] for p in C}
    for src in C:
        for e in aut.out(src):
            O[src] = O[src] | e.cond
            if e.dst in C:
                L[e.dst] = L[e.dst] | e.cond
            else:
                exits[src].append((e.cond, e.dst))
    return L, O, exits


def is_deterministic(L: Dict[int, "buddy.bdd"], h: int) -> bool:
    """The L-partition is deterministic iff each `L(p)` is tight (`⊊ true`, and
    non-empty except possibly the hub, which the anchor covers) and the `L(p)` are
    pairwise disjoint — `partscc`'s input-determinizing condition."""
    states = list(L)
    for p in states:
        if L[p] == buddy.bddtrue or (L[p] == buddy.bddfalse and p != h):
            return False
    for i in range(len(states)):
        for j in range(i + 1, len(states)):
            if (L[states[i]] & L[states[j]]) != buddy.bddfalse:
                return False
    return True
