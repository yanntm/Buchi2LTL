"""The window levels: graded precondition tests and trigger-table builders.

One module per concern (algorithm.md, "k as a parameter"): this is the only
place that knows what a window is. Each level contributes a violation test
(`None` when its preconditions hold, else a one-line reason) and a
`TriggerTable` builder consumed by the level-agnostic assembler in
`label.py`.

* k = 1 — full windows are single letters: per-state triggers `A(s)` at
  offset 1, no truncated windows; the preconditions are anchor's P1/P2
  (tested by `shape.anchored_violation`, reused).
* k = 2 — full windows are adjacent pairs: per-(source, target) triggers
  `I(v) ∧ X g` at offset 2, truncated windows the `q0`-rooted single
  letters `g` at offset 1; the preconditions are P1²/P2²/P0².

The Σ×Σ relations of algorithm.md never materialize. `Enter₂`/`Stay₂` are
unions of *rectangles* `first × second` (both plain letter BDDs), and every
test decomposes: two rectangle unions intersect iff some rectangle pair
intersects coordinate-wise (P1²/P2²), and the park-drop containment
`Stay_k ⊆ Enter_k` is the exact recursive rectangle-cover test `_covered`.
No doubled BDD variables anywhere.
"""

from typing import Dict, List, Optional, Set, Tuple

import spot
import buddy

from .shape import anchored_violation
from .label import TriggerEntry, TriggerTable

__all__ = ["k1_violation", "k1_table", "k2_violation", "k2_table"]

# An in-C non-self edge (source, guard, target); the raw material of windows.
Edge = Tuple[int, "buddy.bdd", int]


def _edges(aut: "spot.twa_graph", C: Set[int]) -> List[Edge]:
    """The in-`C` non-self edges, source-sorted for deterministic output."""
    out: List[Edge] = []
    for src in sorted(C):
        for e in aut.out(src):
            if e.dst != src and e.dst in C:
                out.append((src, e.cond, int(e.dst)))
    return out


def _inputs(L: Dict[int, "buddy.bdd"], A: Dict[int, "buddy.bdd"]
            ) -> Dict[int, "buddy.bdd"]:
    """`I(s) = L(s) ∨ A(s)` — the letters consistent with the run being at
    `s`, the stutter abstraction weakening a window's context components."""
    return {s: L[s] | A[s] for s in L}


def _covered(first: "buddy.bdd", second: "buddy.bdd",
             rects: List[Tuple["buddy.bdd", "buddy.bdd"]]) -> bool:
    """`first × second ⊆ ⋃ rects` — exact. Recursion on the head rectangle
    `(a, b)`: inside `a` the uncovered part of the second coordinate is
    `second ∧ ¬b`; outside `a` nothing is covered. Worst case exponential in
    `len(rects)` (a state's in-edges — small); every step is one BDD op."""
    if first == buddy.bddfalse or second == buddy.bddfalse:
        return True
    if not rects:
        return False
    (a, b), rest = rects[0], rects[1:]
    return (_covered(first & a, second & buddy.bdd_not(b), rest)
            and _covered(first & buddy.bdd_not(a), second, rest))


def _park_redundant(C: Set[int], I: Dict[int, "buddy.bdd"],
                    L: Dict[int, "buddy.bdd"], edges: List[Edge]) -> Set[int]:
    """The targets whose park terms are subsumed: `Stay_k(s) ⊆ Enter_k(s)`,
    i.e. `I(s) × L(s)` covered by the union of `I(v) × g` over the edges
    into `s`."""
    into: Dict[int, List[Tuple["buddy.bdd", "buddy.bdd"]]] = {s: [] for s in C}
    for v, g, s in edges:
        into[s].append((I[v], g))
    return {s for s in C
            if L[s] != buddy.bddfalse and _covered(I[s], L[s], into[s])}


# ---------------------------------------------------------------- k = 1 ----

def k1_violation(L: Dict[int, "buddy.bdd"], A: Dict[int, "buddy.bdd"]
                 ) -> Optional[str]:
    """P1 + P2 — anchor's letter-level preconditions, reused verbatim."""
    return anchored_violation(L, A)


def k1_table(aut: "spot.twa_graph", C: Set[int],
             L: Dict[int, "buddy.bdd"], A: Dict[int, "buddy.bdd"]
             ) -> TriggerTable:
    """Full windows `(A(s), 1, s)` per state, no truncated windows; the park
    drop is `L(s) ⊆ A(s)` (the k = 1 rectangle cover, done directly)."""
    d = aut.get_dict()
    full = [TriggerEntry(spot.bdd_to_formula(A[s], d), 1, s)
            for s in sorted(C) if A[s] != buddy.bddfalse]
    redundant = {s for s in C
                 if L[s] != buddy.bddfalse
                 and (L[s] & buddy.bdd_not(A[s])) == buddy.bddfalse}
    return TriggerTable(full=full, starts=[], park_redundant=redundant)


# ---------------------------------------------------------------- k = 2 ----

def k2_violation(aut: "spot.twa_graph", C: Set[int], q0: int,
                 L: Dict[int, "buddy.bdd"], A: Dict[int, "buddy.bdd"]
                 ) -> Optional[str]:
    """P1² + P2² + P0², decomposed over rectangles:

    * P1² — entering pairs partition: for edges `(v,g,s)`, `(v',g',t)` with
      `s ≠ t`, not both `I(v) ∧ I(v')` and `g ∧ g'` nonempty.
    * P2² — staying pairs fake no entry: for a looping state `s` and an edge
      `(v,g,t)` with `t ≠ s`, not both `I(s) ∧ I(v)` and `L(s) ∧ g` nonempty.
    * P0² — the start is 0-step-anchored: `q0`'s in-`C` out-edge guards
      toward distinct targets (self-loop included) are pairwise disjoint.
    """
    I = _inputs(L, A)
    edges = _edges(aut, C)
    for i, (v, g, s) in enumerate(edges):
        for v2, g2, t in edges[i + 1:]:
            if s != t and (I[v] & I[v2]) != buddy.bddfalse \
                    and (g & g2) != buddy.bddfalse:
                return (f"P1^2: pairs entering states {s} (from {v}) "
                        f"and {t} (from {v2}) overlap")
    for s in sorted(C):
        if L[s] == buddy.bddfalse:
            continue
        for v, g, t in edges:
            if t != s and (I[s] & I[v]) != buddy.bddfalse \
                    and (L[s] & g) != buddy.bddfalse:
                return (f"P2^2: a staying pair at state {s} fires the "
                        f"entry of state {t} (from {v})")
    out0: Dict[int, "buddy.bdd"] = {}
    for e in aut.out(q0):
        if e.dst in C:
            out0[int(e.dst)] = out0.get(int(e.dst), buddy.bddfalse) | e.cond
    targets = sorted(out0)
    for i, t in enumerate(targets):
        for t2 in targets[i + 1:]:
            if (out0[t] & out0[t2]) != buddy.bddfalse:
                return (f"P0^2: q0's out-guards toward states {t} and {t2} "
                        f"overlap (position 0 has no context)")
    return None


def k2_table(aut: "spot.twa_graph", C: Set[int], q0: int,
             L: Dict[int, "buddy.bdd"], A: Dict[int, "buddy.bdd"]
             ) -> TriggerTable:
    """Full windows `(I(v) ∧ X g, 2, s)` grouped per (source, target) pair;
    truncated windows `(g, 1, s)` for `q0`'s in-`C` non-self out-edges; the
    park drop by rectangle cover."""
    d = aut.get_dict()

    def f(bdd: "buddy.bdd") -> "spot.formula":
        return spot.bdd_to_formula(bdd, d)

    I = _inputs(L, A)
    edges = _edges(aut, C)
    grouped: Dict[Tuple[int, int], "buddy.bdd"] = {}
    for v, g, s in edges:
        grouped[(v, s)] = grouped.get((v, s), buddy.bddfalse) | g
    full = [
        TriggerEntry(spot.formula.And([f(I[v]), spot.formula.X(f(g))]), 2, s)
        for (v, s), g in sorted(grouped.items())
    ]
    starts = [
        TriggerEntry(f(g), 1, s)
        for (v, s), g in sorted(grouped.items()) if v == q0
    ]
    return TriggerTable(full=full, starts=starts,
                        park_redundant=_park_redundant(C, I, L, edges))
