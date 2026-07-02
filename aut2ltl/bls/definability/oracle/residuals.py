"""
bls/definability/oracle/residuals.py — the `~lin` base: residual classes of states.

Two states of a deterministic ω-automaton are residual-equivalent when they
accept the same ω-language. The equivalence is computed eagerly (one
language-equivalence check per state × existing class, on the small
deterministic form); the *separator* — an ultimately-periodic word accepted
from exactly one of two inequivalent states — is extracted on demand only,
for the single pair a certificate ends on.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import spot

from ..witness.support import copy_with_init


def _equivalent(a: "spot.twa_graph", b: "spot.twa_graph") -> bool:
    """Language equality of two automata (both containments)."""
    if hasattr(spot, "are_equivalent"):
        return bool(spot.are_equivalent(a, b))
    return bool(spot.contains(a, b)) and bool(spot.contains(b, a))


def state_classes(aut: "spot.twa_graph") -> List[int]:
    """The residual class of every state: `out[q] == out[q']` iff the languages
    accepted from `q` and `q'` are equal. Class ids are dense, in order of
    first appearance."""
    n = aut.num_states()
    rooted = [copy_with_init(aut, q) for q in range(n)]
    classes: List[int] = []
    reps: List[int] = []  # one state per class, in class-id order
    for q in range(n):
        hit: Optional[int] = None
        for cid, r in enumerate(reps):
            if _equivalent(rooted[q], rooted[r]):
                hit = cid
                break
        if hit is None:
            hit = len(reps)
            reps.append(q)
        classes.append(hit)
    return classes


def separator(
    aut: "spot.twa_graph", q: int, qp: int
) -> Optional[Tuple[List[str], List[str]]]:
    """A lasso `(prefix, cycle)` of letter strings accepted from exactly one of
    `q`, `qp` — an ultimately-periodic word separating their residuals — or
    `None` when the residuals are equal."""
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


__all__ = ["state_classes", "separator"]
