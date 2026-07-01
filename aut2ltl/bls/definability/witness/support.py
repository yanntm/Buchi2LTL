"""
bls/definability/witness/support.py — shared primitives for completing a
counting family on a deterministic completed automaton.

Dependency-light helpers used by the linear (`linear.py`) and ω-power
(`omega.py`) completions: rendering a letter valuation, the concrete state
action of a letter word, the closed cycles of that action, shortest reaching
words, re-rooting an automaton, and the minimal period of a cyclic pattern.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional

import spot


def valuation_to_letter(val: Dict[str, bool]) -> str:
    """Render a letter valuation `{ap: bool}` as a Boolean cube, e.g. `a & !b`."""
    lits = [(ap if truth else f"!{ap}") for ap, truth in sorted(val.items())]
    return " & ".join(lits) if lits else "t"


def induced_transform(gens: List[List[int]], factor: List[int]) -> List[int]:
    """The state transformation induced by reading the factor word (1-based
    generator indices), i.e. `s -> state reached by reading the word from s`."""
    n = len(gens[0])
    t = list(range(n))
    for i in factor:
        g = gens[i - 1]
        t = [g[t[s]] for s in range(n)]
    return t


def orbits(t: List[int]) -> List[List[int]]:
    """All closed cycles of the transformation `t` of length >= 2, each as the
    list of its states in `t`-order. States on a transient (leading into a cycle
    but not on it) are never returned: only a closed cycle carries exact
    periodicity — a spiral proves nothing."""
    seen: set = set()
    found: List[List[int]] = []
    for s in range(len(t)):
        if s in seen:
            continue
        path = [s]
        index = {s: 0}
        x = t[s]
        while x not in index and x not in seen:
            index[x] = len(path)
            path.append(x)
            x = t[x]
        if x in index:                       # a new cycle: path[index[x]:]
            cycle = path[index[x]:]
            if len(cycle) >= 2:
                found.append(cycle)
        seen.update(path)
    return found


def word_to(
    gens: List[List[int]],
    valuations: List[Dict[str, bool]],
    init: int,
    target: int,
) -> Optional[List[str]]:
    """A shortest letter word reaching `target` from `init` (BFS over letters),
    or `None` if unreachable."""
    seen: Dict[int, List[str]] = {init: []}
    queue = deque([init])
    while queue:
        s = queue.popleft()
        if s == target:
            return seen[s]
        for li, g in enumerate(gens):
            nxt = g[s]
            if nxt not in seen:
                seen[nxt] = seen[s] + [valuation_to_letter(valuations[li])]
                queue.append(nxt)
    return None


def copy_with_init(aut: "spot.twa_graph", q: int) -> "spot.twa_graph":
    """A deep copy of `aut` whose initial state is `q` (via HOA round-trip —
    robust and cheap on the small minimized automaton)."""
    a = spot.automaton(aut.to_str("hoa"))
    a.set_init_state(q)
    return a


def min_cyclic_period(pattern: List[bool]) -> int:
    """The minimal period of a cyclic boolean pattern: the smallest divisor `q`
    of its length under which a shift by `q` is invariant (the valid shift
    periods of a cyclic sequence form a subgroup of Z_len, so the minimum
    divides the length)."""
    d = len(pattern)
    for q in range(1, d + 1):
        if d % q == 0 and all(pattern[i] == pattern[(i + q) % d] for i in range(d)):
            return q
    return d


__all__ = [
    "valuation_to_letter", "induced_transform", "orbits", "word_to",
    "copy_with_init", "min_cyclic_period",
]
