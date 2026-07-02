"""
bls/definability/oracle/profile.py — the `~ω` seed: the acceptance profile.

`A(q, c)` is the acceptance of iterating the enriched element `c` forever from
state `q`: the state orbit eventually closes into a cycle, the marks `c`
collects around that closed cycle are exactly the ones seen infinitely often,
and the automaton's acceptance condition evaluated on that inf-set decides.
`profile(acc, c)` is the vector of `A(q, c)` over all states — computed in one
`O(|Q|)` pass over the functional graph of `c`'s state map (every state on a
path into a cycle inherits the cycle's verdict: transient marks are finite).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import spot

from ..witness.enriched import Elem

Profile = Tuple[bool, ...]


def profile(acc: "spot.acc_cond", elem: Elem) -> Profile:
    """`A(q, elem)` for every state `q`: walk the functional graph of the
    element's state map, evaluate the acceptance condition on the marks
    collected around each closed cycle, propagate to the transients."""
    n = len(elem)
    out: List[Optional[bool]] = [None] * n
    for start in range(n):
        if out[start] is not None:
            continue
        path: List[int] = []
        pos: Dict[int, int] = {}
        q = start
        while out[q] is None and q not in pos:
            pos[q] = len(path)
            path.append(q)
            q = elem[q][0]
        if out[q] is not None:
            verdict = out[q]
        else:
            inf: Set[int] = set()
            for s in path[pos[q]:]:
                inf |= elem[s][1]
            verdict = bool(acc.accepting(spot.mark_t(sorted(inf))))
        for s in path:
            out[s] = verdict
    return tuple(out)  # type: ignore[arg-type]


__all__ = ["Profile", "profile"]
