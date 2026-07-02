"""
bls/definability/oracle/refine.py — the congruence: seed refinement and the chase.

`refine` computes the coarsest equivalence that refines a seed labelling and
is stable under right-multiplication by the letter generators — Moore-style
partition refinement over the monoid's right-translation table. When the seed
components are themselves right-invariant properties, the fixpoint is the
syntactic congruence restricted to the materialized monoid.

`chase` is the constructive counterpart, run on demand with no bookkeeping
kept by `refine`: for two elements the fixpoint separates, a shortest word
`b` with `seed(e·b) ≠ seed(f·b)` is found by BFS over the pair graph of the
right-translation table — the distinguishing-word construction run forward.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, Hashable, List, Optional, Sequence, Set, Tuple

from .closure import Monoid


def _canon(keys: Sequence[Hashable]) -> List[int]:
    """Dense ids in order of first appearance."""
    seen: Dict[Hashable, int] = {}
    out: List[int] = []
    for k in keys:
        if k not in seen:
            seen[k] = len(seen)
        out.append(seen[k])
    return out


def refine(mon: Monoid, seed: Sequence[Hashable]) -> List[int]:
    """The coarsest refinement of `seed` stable under every right-translation
    `e ↦ e·letter` of `mon` — class ids per element. Each round appends the
    classes of all letter-successors to each element's label; the class count
    is non-decreasing and bounded by `len(mon)`, so the loop terminates."""
    labels = _canon(seed)
    while True:
        sigs: List[Tuple[int, Tuple[int, ...]]] = [
            (labels[e], tuple(labels[j] for j in mon.right[e]))
            for e in range(len(mon))
        ]
        new = _canon(sigs)
        if max(new) == max(labels):
            return new
        labels = new


def chase(
    mon: Monoid, seed: Sequence[Hashable], e: int, f: int
) -> Optional[List[int]]:
    """A shortest word `b` (0-based letter indices, possibly empty) with
    `seed[e·b] != seed[f·b]`, or `None` when no word separates the pair —
    which cannot happen for a pair `refine` separated."""
    if seed[e] != seed[f]:
        return []
    seen: Set[Tuple[int, int]] = {(e, f)}
    queue: "deque[Tuple[int, int, List[int]]]" = deque([(e, f, [])])
    while queue:
        a, b, word = queue.popleft()
        for li in range(len(mon.right[a])):
            a2, b2 = mon.right[a][li], mon.right[b][li]
            if a2 == b2:
                continue  # equal elements can never separate again
            nxt = word + [li]
            if seed[a2] != seed[b2]:
                return nxt
            if (a2, b2) not in seen:
                seen.add((a2, b2))
                queue.append((a2, b2, nxt))
    return None


__all__ = ["refine", "chase"]
