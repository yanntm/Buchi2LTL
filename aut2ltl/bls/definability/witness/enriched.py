"""
bls/definability/witness/enriched.py — the acceptance-enriched monoid of a
deterministic completed automaton.

The transition monoid forgets the acceptance marks a word collects along its
path — exactly the information an ω-power counting family lives on. The
enriched element of a word `w` maps each state `q` to the pair
`(δ(q, w), marks collected from q along w)`; elements compose as

    (f, M) · (g, N) : q ↦ ( g(f(q)), M(q) ∪ N(f(q)) )

so the enriched monoid is a finite transformation monoid on `Q × 2^C` (`C` the
acceptance marks). Two words with equal enriched elements induce identical run
skeletons from every state — same state sequence, same per-segment marks —
hence equal acceptance in any lasso context. This module builds the letter
elements, composes them, computes the index/period of a power sequence, and
enumerates one shortest representative word per element (BFS) — the candidate
space for the ω-power return word.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, FrozenSet, Iterator, List, Optional, Tuple

import buddy
import spot

from .support import valuation_to_letter

# One enriched element: per state, (destination, marks collected on the way).
Elem = Tuple[Tuple[int, FrozenSet[int]], ...]


def letter_elems(
    aut: "spot.twa_graph", valuations: List[Dict[str, bool]]
) -> List[Elem]:
    """The enriched element of each letter: for every state, the (unique on a
    deterministic complete automaton) outgoing edge the letter satisfies, as
    `(destination, acceptance marks of that edge)`."""
    n = aut.num_states()
    d = aut.get_dict()
    elems: List[Elem] = []
    for val in valuations:
        cube = spot.formula_to_bdd(spot.formula(valuation_to_letter(val)), d, aut)
        entry: List[Tuple[int, FrozenSet[int]]] = []
        for s in range(n):
            hit: Optional[Tuple[int, FrozenSet[int]]] = None
            for e in aut.out(s):
                if (e.cond & cube) != buddy.bddfalse:
                    hit = (e.dst, frozenset(e.acc.sets()))
                    break
            if hit is None:
                raise ValueError(f"state {s}: no edge for letter {valuation_to_letter(val)}")
            entry.append(hit)
        elems.append(tuple(entry))
    return elems


def compose(e1: Elem, e2: Elem) -> Elem:
    """The enriched element of `w1.w2` from those of `w1` and `w2`."""
    return tuple((e2[dst][0], marks | e2[dst][1]) for (dst, marks) in e1)


def elem_of_factor(letters: List[Elem], factor: List[int]) -> Elem:
    """The enriched element of a word given as 1-based letter indices."""
    e = letters[factor[0] - 1]
    for i in factor[1:]:
        e = compose(e, letters[i - 1])
    return e


def power_index_period(e: Elem, cap: int) -> Optional[Tuple[int, int]]:
    """The index `a` and period `c` of the power sequence `e, e², …` — the
    minimal `a >= 1, c >= 1` with `e^{a+c} = e^a` — or `None` when the sequence
    does not close within `cap` powers."""
    seen: Dict[Elem, int] = {}
    cur = e
    k = 1
    while cur not in seen:
        if k > cap:
            return None
        seen[cur] = k
        cur = compose(cur, e)
        k += 1
    a = seen[cur]
    return (a, k - a)


def bfs_words(
    letters: List[Elem], letter_names: List[str], cap: int
) -> Iterator[Tuple[List[str], Elem]]:
    """Enumerate distinct enriched elements with one shortest representative
    word each, shortest-first (BFS over right-multiplication by letters), up to
    `cap` elements. A return word matters only through its enriched element, so
    this is the exhaustive candidate stream, truncated at `cap`."""
    seen: set = set()
    queue: deque = deque()
    for name, e in zip(letter_names, letters):
        if e not in seen:
            seen.add(e)
            queue.append(([name], e))
    yielded = 0
    while queue and yielded < cap:
        word, e = queue.popleft()
        yield (word, e)
        yielded += 1
        for name, le in zip(letter_names, letters):
            ne = compose(e, le)
            if ne not in seen:
                seen.add(ne)
                queue.append((word + [name], ne))


__all__ = ["Elem", "letter_elems", "compose", "elem_of_factor",
           "power_index_period", "bfs_words"]
