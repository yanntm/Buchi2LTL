"""
bls/definability/oracle/quotient.py — the algebra: aperiodicity of the quotient.

Power-iterates every class of the quotient monoid. The class of `v^{k+1}` is
determined by the classes of `v^k` and `v` (the relation is a congruence), so
the class power sequence is detected by its first repeated class id — which
also makes the index minimal and the classes around the cycle pairwise
distinct. Every period 1 ⟹ the quotient is aperiodic. Otherwise the first
group found (elements are scanned in BFS order, so its representative word is
shortest) is returned with its full power ladder for the extraction step.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .closure import Monoid


@dataclass
class Group:
    """A non-aperiodic power cycle in the quotient: the element `v` (index into
    the monoid), the index `a ≥ 1` and period `c > 1` of its *class* power
    sequence, and `powers[k] =` the monoid index of `v^{k+1}` for
    `k = 0 … a+c-2` — the ladder the certificate is unrolled on."""

    v: int
    a: int
    c: int
    powers: List[int]


def find_group(mon: Monoid, cls: List[int]) -> Optional[Group]:
    """The first group class of the quotient `mon / cls` in BFS element order,
    or `None` when every class power sequence has period 1 (aperiodic)."""
    visited: Set[int] = set()
    for e in range(1, len(mon)):  # 0 is the identity: idempotent, period 1
        if cls[e] in visited:
            continue  # the class sequence depends only on the starting class
        visited.add(cls[e])
        powers: List[int] = [e]
        seen: Dict[int, int] = {cls[e]: 1}
        cur = e
        k = 1
        while True:
            cur = mon.mult(cur, e)
            k += 1
            c0 = cls[cur]
            if c0 in seen:
                a = seen[c0]
                c = k - a
                if c > 1:
                    return Group(v=e, a=a, c=c, powers=powers)
                break
            seen[c0] = k
            powers.append(cur)
    return None


__all__ = ["Group", "find_group"]
