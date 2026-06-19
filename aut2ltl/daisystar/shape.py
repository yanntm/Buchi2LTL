"""Star-hub structure helpers behind the `daisystar` reachability peel.

A **daisystar SCC** is the initial state's SCC `C` presented as a length-1 star,
*in the reachability regime*: a hub `h` (the init state) with **petals**
(self-loops `h → h`) and **hub-stems** (exits `h → dst ∉ C`), while every other
state `s ∈ C` is one hop from `h` — a **spoke** with an entry `h → s`, an optional
self-loop **body** `s → s`, a return `s → h`, and optionally **spoke-stems**
`s → dst ∉ C` (exits taken *from inside* a spoke). No edge from a spoke to a third
in-`C` state (that would be a length-2 detour — full daisychain, not this peel).

This differs from `daisy2`'s `star_partition` in two ways, both because daisystar
is the *rejecting* (reachability) regime where `STAY∞` is `false`:

* spoke-exits are **allowed** (daisy2 rejects an edge leaving `C` from a spoke);
* acceptance **marks are ignored** (no `STAY∞`, so no link-mark bookkeeping).

`star_partition` is the accept/decline test and the partition in one pass:
`None` exactly when `C` is not such a star, else `(petals, spokes, hub_stems)`.
`reroot` (reused from `aut2ltl.daisy.shape`) builds `A↓dst` for a stem child.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import spot

from aut2ltl.daisy.shape import reroot  # reused verbatim: A↓dst for stem delegation

# A stem is an exit's (guard, destination state ∉ C).
Stem = Tuple["spot.formula", int]


@dataclass
class Spoke:
    """A length-1 detour `h → s → h`, possibly with exits. `entry`/`body`/`ret`
    are the aggregate role guards (E_s / G_s / R_s) used to build the moves
    `E_s ∧ X(G_s U R_s)` (stay) and `E_s ∧ X(G_s U (h_k ∧ X φ_k))` (leave via the
    spoke). `stems` are the spoke's own exits out of `C`. Marks are irrelevant
    here — daisystar's SCC is rejecting, so there is no `STAY∞` to count them."""

    state: int
    entry: "spot.formula"
    body: "spot.formula"
    ret: "spot.formula"
    stems: List[Stem] = field(default_factory=list)


def init_scc_states(aut: "spot.twa_graph", h: int) -> Set[int]:
    """The states of the SCC containing the initial state `h` — the component `C`
    daisystar peels."""
    si = spot.scc_info(aut)
    return {int(s) for s in si.states_of(si.scc_of(h))}


def _f(aut: "spot.twa_graph", cond: "buddy.bdd") -> "spot.formula":
    """A guard BDD as a `spot.formula`."""
    return spot.bdd_to_formula(cond, aut.get_dict())


def _or(fs: List["spot.formula"]) -> "spot.formula":
    """Disjunction of `fs`; the empty disjunction is `false`."""
    return spot.formula.Or(fs) if fs else spot.formula.ff()


def star_partition(
    aut: "spot.twa_graph", h: int
) -> Optional[Tuple[List["spot.formula"], List[Spoke], List[Stem]]]:
    """Partition the initial SCC into petals, spokes and hub-stems, or `None` if it
    is not a length-1 star hub at `h`. One pass over the hub's and the spokes'
    out-edges; a spoke's out-edges may only target itself (body), the hub (return)
    or outside `C` (a spoke-stem) — an edge to a third in-`C` state is a length-2
    detour and declines. The SCC boundary (no entry from outside `C`) holds for
    free: `C` is the *initial* SCC, so nothing outside it reaches back in."""
    C = init_scc_states(aut, h)

    petals: List["spot.formula"] = []
    hub_stems: List[Stem] = []
    entries: Dict[int, List["spot.formula"]] = {}   # spoke state -> its h→s guards
    for e in aut.out(h):
        g = _f(aut, e.cond)
        if e.dst == h:
            petals.append(g)
        elif e.dst in C:
            entries.setdefault(e.dst, []).append(g)
        else:
            hub_stems.append((g, e.dst))

    spokes: List[Spoke] = []
    for s in C:
        if s == h:
            continue
        if s not in entries:
            return None                      # in C but no direct entry: not a star
        body_g: List["spot.formula"] = []
        ret_g: List["spot.formula"] = []
        stems: List[Stem] = []
        for e in aut.out(s):
            g = _f(aut, e.cond)
            if e.dst == s:
                body_g.append(g)
            elif e.dst == h:
                ret_g.append(g)
            elif e.dst in C:
                return None                  # edge to a third in-C state: detour > 1
            else:
                stems.append((g, e.dst))     # a spoke-exit (allowed here)
        if not ret_g and not stems:
            return None                      # neither returns nor exits: malformed
        spokes.append(Spoke(
            state=s,
            entry=_or(entries[s]),
            body=_or(body_g),
            ret=_or(ret_g),
            stems=stems,
        ))

    return petals, spokes, hub_stems
