"""
bls/definability/witness/witness.py — extract non-LTL witness material.

`extract_witness(lang)` reads the same form as the definability gate
(`det_generic_minimal`, completed) and, on the non-aperiodic branch, returns the
period word `v` and period `p` of the counting family `(u, v, x, p)`: the group
element lifted to concrete letters, and its order. Stage 1 produces `(v, p)`;
`u` / `x` (completing the family) come later. See algorithm.md.
"""

from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

import spot

from aut2ltl.witness import Witness
from aut2ltl.bls.extract import extract_generators
from aut2ltl.bls.gap.witness_group import witness_group

if TYPE_CHECKING:
    from aut2ltl.language import Language


def _valuation_to_letter(val: Dict[str, bool]) -> str:
    """Render a letter valuation `{ap: bool}` as a Boolean cube, e.g. `a & !b`."""
    lits = [(ap if truth else f"!{ap}") for ap, truth in sorted(val.items())]
    return " & ".join(lits) if lits else "t"


# --- stage 2: completing the family (u, x) from the automaton ---------------- #

def _induced_transform(gens: List[List[int]], factor: List[int]) -> List[int]:
    """The state transformation induced by reading the factor word `v` (1-based
    generator indices), i.e. `s -> state reached by reading v from s`."""
    n = len(gens[0])
    t = list(range(n))
    for i in factor:
        g = gens[i - 1]
        t = [g[t[s]] for s in range(n)]
    return t


def _cycle_state(t: List[int], p: int) -> Optional[int]:
    """A state lying on a `t`-cycle of length exactly `p` (a non-trivial phase to
    anchor the family on), or `None`."""
    for s in range(len(t)):
        orbit = [s]
        x = t[s]
        while x not in orbit:
            orbit.append(x)
            x = t[x]
        if x == s and len(orbit) == p:
            return s
    return None


def _word_to(
    gens: List[List[int]],
    valuations: List[Dict[str, bool]],
    init: int,
    target: int,
) -> Optional[List[str]]:
    """A shortest letter word reaching `target` from `init` (BFS over letters), or
    `None` if unreachable."""
    from collections import deque

    seen = {init: []}  # type: Dict[int, List[str]]
    queue = deque([init])
    while queue:
        s = queue.popleft()
        if s == target:
            return seen[s]
        for li, g in enumerate(gens):
            nxt = g[s]
            if nxt not in seen:
                seen[nxt] = seen[s] + [_valuation_to_letter(valuations[li])]
                queue.append(nxt)
    return None


def _copy_with_init(aut: "spot.twa_graph", q: int) -> "spot.twa_graph":
    """A deep copy of `aut` whose initial state is `q` (via HOA round-trip — robust
    and cheap on the small minimized automaton)."""
    a = spot.automaton(aut.to_str("hoa"))
    a.set_init_state(q)
    return a


def _distinguish(
    aut: "spot.twa_graph", q: int, qp: int
) -> Optional[tuple]:
    """A lasso `(prefix, cycle)` of letter strings separating the residuals of `q`
    and `qp` — accepted from one, rejected from the other — or `None`."""
    aq = _copy_with_init(aut, q)
    aqp = _copy_with_init(aut, qp)
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


def _complete_family(
    w: "Witness",
    aut: "spot.twa_graph",
    gens: List[List[int]],
    valuations: List[Dict[str, bool]],
) -> None:
    """Fill `w.u` / `w.x_*` (best-effort): anchor on a state of a `p`-cycle of the
    `v`-transformation, reach it with `u`, and separate it from its next phase with
    `x`. Leaves them `None` if no anchor / separator is found."""
    t = _induced_transform(gens, w.factor)
    q = _cycle_state(t, w.p)
    if q is None:
        return
    u = _word_to(gens, valuations, aut.get_init_state_number(), q)
    dist = _distinguish(aut, q, t[q])
    if u is not None and dist is not None:
        w.u = u
        w.x_prefix, w.x_cycle = dist


def extract_witness(
    lang: "Language",
    *,
    complete: bool = False,
    gap_cmd: str = "gap",
    timeout: int = 60,
    max_aps: int = 5,
) -> Optional[Witness]:
    """Return the witness material for a non-LTL `lang`, or `None` when the
    transition monoid carries no group (an aperiodic / LTL-definable language).

    Reads `det_generic_minimal()`, completes it, extracts the letter generators
    (keeping the valuations, unlike the gate), drives the witness GAP script, and
    lifts its factorization back to the period word `v`. With `complete=True` it
    also synthesises the family completion `u` / `x` from the automaton (best-effort).
    """
    det = lang.det_generic_minimal()
    aut = spot.postprocess(det, "deterministic", "generic", "complete")
    gens, _masks, valuations = extract_generators(aut, max_aps=max_aps)
    raw = witness_group(gens, gap_cmd=gap_cmd, timeout=timeout)
    if raw is None:
        return None
    v = [_valuation_to_letter(valuations[i - 1]) for i in raw.factor]
    w = Witness(p=raw.period, v=v, factor=list(raw.factor))
    if complete:
        _complete_family(w, aut, gens, valuations)
    return w


__all__ = ["extract_witness"]
