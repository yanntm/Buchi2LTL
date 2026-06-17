"""Σ and the care-set strip — the BDD mechanics behind the `inv` decorator.

`sigma(A)` is the disjunction of all of `A`'s edge guards: a Boolean over `AP`
that every transition's guard implies, hence a global safety invariant of `L(A)`
(every letter any accepted word reads satisfies it). `strip(A, Σ)` rewrites each
guard by the Coudert–Madre restrict under care-set `Σ` (`buddy.bdd_simplify`): the
guard is preserved wherever `Σ` holds and free on `¬Σ`, the letters no edge admits.
See README.md.
"""

from typing import TYPE_CHECKING

import spot
import buddy

if TYPE_CHECKING:  # annotation-only; buddy/spot are imported above for runtime use
    pass


def sigma(aut: "spot.twa_graph") -> "buddy.bdd":
    """`Σ = ⋁ { g : (·, g, ·, ·) ∈ δ }` — the disjunction of all edge guards.

    `bddfalse` when the automaton has no edges; `bddtrue` when the guards already
    cover `2^AP` (the vacuous case the decorator short-circuits)."""
    acc = buddy.bddfalse
    for s in range(aut.num_states()):
        for e in aut.out(s):
            acc = acc | e.cond
            if acc == buddy.bddtrue:
                return acc                 # O(1): Σ can only stay true (vacuous case)
    return acc


def strip(aut: "spot.twa_graph", care: "buddy.bdd") -> "spot.twa_graph":
    """A copy of `aut` with every edge guard simplified under care-set `care`
    (Coudert–Madre restrict, `buddy.bdd_simplify`). State numbering, acceptance and
    atomic propositions are preserved, and on `care`-letters every simplified guard
    agrees with its original — so the copy is interchangeable with `aut` there."""
    d = aut.get_dict()
    out = spot.make_twa_graph(d)
    out.copy_ap_of(aut)
    out.set_acceptance(aut.acc())
    for _ in range(aut.num_states()):
        out.new_state()
    for s in range(aut.num_states()):
        for e in aut.out(s):
            out.new_edge(s, e.dst, buddy.bdd_simplify(e.cond, care), e.acc)
    out.set_init_state(aut.get_init_state_number())
    return out
