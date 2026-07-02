"""
bls/definability/oracle/residuals.py — the `~lin` base: residual classes of states.

Two states of a deterministic ω-automaton are residual-equivalent when they
accept the same ω-language. The equivalence is computed eagerly by Spot's
`language_map` — the exact primitive: one dualized complement per state
(cheap on a deterministic form), pairwise on-the-fly intersection checks
against one representative per class. The *separator* — an ultimately-periodic
word accepted from exactly one of two inequivalent states — is extracted on
demand only, for the single pair a certificate ends on.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import spot

from ..witness.support import copy_with_init


def state_classes(aut: "spot.twa_graph") -> List[int]:
    """The residual class of every state: `out[q] == out[q']` iff the languages
    accepted from `q` and `q'` are equal (`spot.language_map`; the class id is
    the smallest state index recognizing the language — stable labels, not
    dense ones)."""
    return list(spot.language_map(aut))


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
