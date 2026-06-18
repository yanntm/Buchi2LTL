"""Star-hub structure helpers behind the `daisy2` combinator (see algorithm2.md).

A **length-1 star hub** is the initial state's SCC `C` presented as: a hub `h`
(the init state) carrying **petals** (self-loops `h → h`) and **stems** (exits
`h → dst ∉ C`), while every *other* state `s ∈ C` is one hop from `h` — a
**spoke** with an entry `h → s`, an optional self-loop **body** `s → s`, and a
return `s → h`, and **no edge to any third state** (the "length 1 in states"
hypothesis). It is daisy's fragment widened by one level: each spoke is itself a
one-state daisy.

`star_partition` is the accept/decline test *and* the partition in one pass: it
returns `None` exactly when `C` is not such a star, else `(petals, spokes,
stems)`. `reroot` (reused from `aut2ltl.daisy.shape`) builds the sub-automaton
`A↓dst` handed to the child for a stem.
"""

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

import spot

from aut2ltl.daisy.shape import reroot  # reused verbatim: A↓dst for stem delegation

# A petal is a hub self-loop's (guard, acceptance sets); a stem is a hub exit's
# (guard, destination state ∉ C).
Petal = Tuple["spot.formula", FrozenSet[int]]
Stem = Tuple["spot.formula", int]


@dataclass
class Spoke:
    """A length-1 detour `h → s → h`: the entry guard (`h → s`), the body guard
    (`s → s` self-loop, `false` if the spoke has none), the return guard
    (`s → h`), and the acceptance sets marked on each role **separately** —
    `entry_acc`, `body_acc`, `ret_acc`. The roles must stay split because a body
    mark is collected only when the body actually loops, while entry/return marks
    are collected on every traversal (see algorithm2.md §Acceptance)."""

    state: int
    entry: "spot.formula"
    body: "spot.formula"
    ret: "spot.formula"
    entry_acc: FrozenSet[int]
    body_acc: FrozenSet[int]
    ret_acc: FrozenSet[int]


def init_scc_states(aut: "spot.twa_graph") -> Set[int]:
    """The states of the SCC containing the initial state — the component `C`
    daisy2 peels."""
    si = spot.scc_info(aut)
    h = aut.get_init_state_number()
    return {int(s) for s in si.states_of(si.scc_of(h))}


def _f(aut: "spot.twa_graph", cond: "buddy.bdd") -> "spot.formula":
    """A guard BDD as a `spot.formula`."""
    return spot.bdd_to_formula(cond, aut.get_dict())


def _or(fs: List["spot.formula"]) -> "spot.formula":
    """Disjunction of `fs`; the empty disjunction is `false`."""
    return spot.formula.Or(fs) if fs else spot.formula.ff()


def star_partition(
    aut: "spot.twa_graph", h: int
) -> Optional[Tuple[List[Petal], List[Spoke], List[Stem]]]:
    """Partition the initial SCC into petals, spokes and stems, or `None` if it is
    not a length-1 star hub at `h`. One pass over the hub's and the spokes'
    out-edges; the spoke test (every non-hub out-edge targets `h` or itself) is
    exactly the "length 1 in states" precondition. The SCC boundary (no entry
    from outside `C`) holds automatically: `C` is the *initial* SCC, so nothing
    outside it can reach back in."""
    C = init_scc_states(aut)

    petals: List[Petal] = []
    stems: List[Stem] = []
    entries: Dict[int, List[Petal]] = {}     # spoke state -> its h→s entry edges
    for e in aut.out(h):
        edge: Petal = (_f(aut, e.cond), frozenset(e.acc.sets()))
        if e.dst == h:
            petals.append(edge)
        elif e.dst in C:
            entries.setdefault(e.dst, []).append(edge)
        else:
            stems.append((edge[0], e.dst))

    spokes: List[Spoke] = []
    for s in C:
        if s == h:
            continue
        if s not in entries:
            return None                      # in C but no direct entry: not a star
        body_g: List["spot.formula"] = []
        ret_g: List["spot.formula"] = []
        body_acc: Set[int] = set()
        ret_acc: Set[int] = set()
        for e in aut.out(s):
            if e.dst == s:
                body_g.append(_f(aut, e.cond))
                body_acc |= set(e.acc.sets())
            elif e.dst == h:
                ret_g.append(_f(aut, e.cond))
                ret_acc |= set(e.acc.sets())
            else:
                return None                  # edge to a third state: detour > length 1
        if not ret_g:
            return None                      # cannot return to h (not in the SCC)
        entry_acc: Set[int] = set(a for _, sets in entries[s] for a in sets)
        spokes.append(Spoke(
            state=s,
            entry=_or([g for g, _ in entries[s]]),
            body=_or(body_g),
            ret=_or(ret_g),
            entry_acc=frozenset(entry_acc),
            body_acc=frozenset(body_acc),
            ret_acc=frozenset(ret_acc),
        ))

    return petals, spokes, stems
