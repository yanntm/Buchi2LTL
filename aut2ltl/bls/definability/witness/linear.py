"""
bls/definability/witness/linear.py — complete the LINEAR counting family shape.

Given a deterministic completed automaton, its letter generators and a period
word `v` (the lifted group element carried by the `Witness`), fill the witness
with `(u, x, p)` such that membership of `u . v^n . x` toggles with `n mod p`:

  * anchor   — every closed cycle of `v`'s induced state action, length >= 2;
  * reach    — `u`: a shortest word from the initial state to the cycle;
  * separate — `x`: for EVERY phase pair of the cycle, a lasso accepted from
    one phase and rejected from the other (residual product emptiness). A count
    can surface between non-adjacent phases only, so adjacent-only comparison
    is sound but incomplete.

The declared period is the minimal cyclic period of the membership pattern of
`x` around the whole cycle — the toggling period, not necessarily the group
order (a separator between phases i and j with gcd(|cycle|, j-i) > 1 toggles
with a proper divisor).

Returns False (witness untouched) when no cycle is reachable or no phase pair
separates. On a form whose orbit phases are residual-equal — any
prefix-independent language — that failure is structural, not a miss: the
ω-power shape (`omega.py`) is the discriminator there.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import spot

from aut2ltl.verifier import member
from .support import copy_with_init, induced_transform, min_cyclic_period, orbits, word_to

if TYPE_CHECKING:
    from aut2ltl.witness import Witness


def _distinguish(
    aut: "spot.twa_graph", q: int, qp: int
) -> Optional[Tuple[List[str], List[str]]]:
    """A lasso `(prefix, cycle)` of letter strings separating the residuals of
    `q` and `qp` — accepted from one, rejected from the other — or `None`."""
    aq = copy_with_init(aut, q)
    aqp = copy_with_init(aut, qp)
    for first, second in ((aq, aqp), (aqp, aq)):
        prod = spot.product(first, spot.complement(second))
        word = prod.accepting_word()
        if word is not None:
            word.simplify()
            d = prod.get_dict()
            prefix = [str(spot.bdd_to_formula(b, d)) for b in word.prefix]
            cycle = [str(spot.bdd_to_formula(b, d)) for b in word.cycle]
            return prefix, cycle
    return None


def _lasso_str(prefix: List[str], cycle: List[str]) -> str:
    """Render a lasso as a Spot word string."""
    return "; ".join(prefix + ["cycle{" + "; ".join(cycle) + "}"])


def complete_linear(
    w: "Witness",
    aut: "spot.twa_graph",
    gens: List[List[int]],
    valuations: List[Dict[str, bool]],
) -> bool:
    """Try to fill `w.u` / `w.x_*` / `w.p` (the linear shape) over all reachable
    cycles of `v`'s action and all phase pairs. True on success."""
    t = induced_transform(gens, w.factor)
    init = aut.get_init_state_number()
    for cycle in orbits(t):
        u = word_to(gens, valuations, init, cycle[0])
        if u is None:
            continue
        d = len(cycle)
        for i in range(d):
            for j in range(i + 1, d):
                dist = _distinguish(aut, cycle[i], cycle[j])
                if dist is None:
                    continue
                x_prefix, x_cycle = dist
                x = _lasso_str(x_prefix, x_cycle)
                # The family's membership around the whole cycle: phase k is the
                # state reached by u.v^k, so the pattern below IS n -> [u.v^n.x].
                pattern = [member(copy_with_init(aut, cycle[k]), x) for k in range(d)]
                p = min_cyclic_period(pattern)
                if p <= 1:
                    continue  # read-back did not confirm the separator; keep looking
                w.u, w.x_prefix, w.x_cycle, w.p = u, x_prefix, x_cycle, p
                return True
    return False


__all__ = ["complete_linear"]
