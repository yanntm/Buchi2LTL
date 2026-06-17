"""Per-state labels and the partition test behind the `partscc` leaf.

For a single terminal SCC, each state `s` gets a label `L(s) = ⋁(guards entering
s)` (`incoming_or`) that should uniquely characterize it, and `O(s) = ⋁(guards
leaving s)` (`outgoing_or`) — its next-step availability. `partition` returns the
`L`-map iff the labels are tight and pairwise disjoint (the input-determinizing
condition), else `None`. The disjointness *is* the determinization. See
algorithm.md.
"""

from typing import Dict, List, Optional

import spot
import buddy


def scc_states(aut: "spot.twa_graph") -> Optional[List[int]]:
    """The reachable states of `aut` when it is a **single SCC of size ≥ 2**, else
    `None`. A single SCC is strongly connected and — being the whole automaton —
    escape-free; that is the entire structural precondition partscc accepts."""
    si = spot.scc_info(aut)
    if si.scc_count() != 1:
        return None
    states = [int(s) for s in si.states_of(0)]
    return states if len(states) >= 2 else None


def incoming_or(aut: "spot.twa_graph", state: int, states: List[int]) -> "buddy.bdd":
    """`L(s) = ⋁ { g : (src, g, s, ·) ∈ δ, src ∈ states }` — the disjunction of
    guards on edges (within the SCC) entering `state`."""
    res = buddy.bddfalse
    for src in states:
        for e in aut.out(src):
            if e.dst == state:
                res = res | e.cond
                if res == buddy.bddtrue:
                    return res             # O(1): a true label fails tightness anyway
    return res


def outgoing_or(aut: "spot.twa_graph", state: int) -> "buddy.bdd":
    """`O(s) = ⋁ { g : (s, g, ·, ·) ∈ δ }` — the disjunction of guards on edges
    leaving `state`."""
    res = buddy.bddfalse
    for e in aut.out(state):
        res = res | e.cond
        if res == buddy.bddtrue:
            return res
    return res


def partition(aut: "spot.twa_graph", states: List[int]) -> Optional[Dict[int, "buddy.bdd"]]:
    """The labels `{s: L(s)}` iff they form a usable partition — each strictly
    tighter than `true` (and non-empty) and pairwise mutually exclusive — else
    `None`. Pairwise disjointness is what makes the state recoverable from the last
    letter, hence eliminable."""
    labels = {s: incoming_or(aut, s, states) for s in states}
    for lab in labels.values():
        if lab == buddy.bddtrue or lab == buddy.bddfalse:
            return None                          # not tight / empty: unusable label
    for i in range(len(states)):
        for j in range(i + 1, len(states)):
            if (labels[states[i]] & labels[states[j]]) != buddy.bddfalse:
                return None                      # overlap: not a partition
    return labels
