"""The anchor read-off: `Final = STAY∞ ∨ LEAVE` from the L/A/M/E labels.

Builds the label of an anchored component (algorithm.md, "The label"): the
per-state sojourn `L(s) W M(s)`, the anchored transition law `step`, the
parking-aware fairness over the states carrying every color (`F_all`), the
loop-then-exit `leave(s)`, and the two branches sharing them. Free functions,
so a probe can inspect the exact formula a translator adopts; the only spot
work is formula construction and `bdd_to_formula`.

Degenerate inputs need no cases here: empty guards collapse the connectives
(`W`/`U`/`G`/`F` over `false`, empty conjunctions/disjunctions), so a loop-free,
exit-free, rejecting, or single-state component yields the reduced forms the
algorithm derives. The explicit `bddfalse` short-circuits below only keep the
built term small; they never change its language.
"""

from typing import Dict, List, Set, Tuple

import spot
import buddy

__all__ = ["build_final"]

_F = spot.formula


def _or(fs: List["spot.formula"]) -> "spot.formula":
    return _F.Or(fs) if fs else _F.ff()


def _and(fs: List["spot.formula"]) -> "spot.formula":
    return _F.And(fs) if fs else _F.tt()


def build_final(
    aut: "spot.twa_graph", C: Set[int], q0: int,
    L: Dict[int, "buddy.bdd"], A: Dict[int, "buddy.bdd"], M: Dict[int, "buddy.bdd"],
    exits: Dict[int, List[Tuple["buddy.bdd", int]]],
    phi: Dict[int, "spot.formula"],
) -> "spot.formula":
    """The label `Final = STAY∞ ∨ LEAVE` of the anchored component `C` with
    initial state `q0`, from its L/A/M/E data and the child labels `phi`
    (`exit target → formula`). Assumes the anchored precondition holds and the
    acceptance of `aut` is state-based generalized Büchi."""
    d = aut.get_dict()

    def f(bdd: "buddy.bdd") -> "spot.formula":
        return spot.bdd_to_formula(bdd, d)

    states = sorted(C)

    def sojourn(s: int) -> "spot.formula":
        # L(s) W M(s); collapsed when an arm is empty (false W m = m, l W false = G l).
        if L[s] == buddy.bddfalse:
            return f(M[s])
        if M[s] == buddy.bddfalse:
            return _F.G(f(L[s]))
        return _F.W(f(L[s]), f(M[s]))

    def leave(s: int) -> "spot.formula":
        # L(s) U (exit now, child next); false when s has no exit.
        exit_or = _or([_F.And([f(g), _F.X(phi[dst])]) for g, dst in exits[s]])
        if exit_or == _F.ff() or L[s] == buddy.bddfalse:
            return exit_or
        return _F.U(f(L[s]), exit_or)

    # step = ⋀_s ( A(s) → X sojourn(s) ) — the anchored transition law, per position.
    step = _and([
        _F.Or([_F.Not(f(A[s])), _F.X(sojourn(s))])
        for s in states if A[s] != buddy.bddfalse
    ])

    # fair = every color anchored infinitely often, or park on an F_all state,
    # or park on q0 from position 0 (construction-time membership tests).
    m = aut.num_sets()
    colors: Dict[int, Set[int]] = {s: set(aut.state_acc_sets(s).sets()) for s in states}
    every_color = _and([
        _F.G(_F.F(_or([f(A[s]) for s in states if i in colors[s]])))
        for i in range(m)
    ])
    f_all = [s for s in states if len(colors[s]) == m]
    fair_parts = [every_color]
    if m > 0:                                   # m = 0: every_color is already true
        def park_redundant(s: int) -> bool:
            # L(s) ⊆ A(s): every letter of a park at s fires s's own anchor, so
            # the every_color disjunct already covers the parked run. Sound only
            # because s ∈ F_all — A(s) then witnesses every color's GF at once.
            return (L[s] & buddy.bdd_not(A[s])) == buddy.bddfalse

        fair_parts += [
            _F.And([f(A[s]), _F.X(_F.G(f(L[s])))])       # F park(s) below
            for s in f_all
            if A[s] != buddy.bddfalse and L[s] != buddy.bddfalse
            and not park_redundant(s)
        ]
        fair_parts = [fair_parts[0]] + [_F.F(p) for p in fair_parts[1:]]
        if q0 in f_all and L[q0] != buddy.bddfalse \
                and not park_redundant(q0):              # [ q0 ∈ F_all ] ∧ G L(q0)
            fair_parts.append(_F.G(f(L[q0])))
    fair = _or(fair_parts)

    stay = _and([sojourn(q0), _F.G(step), fair])

    # LEAVE = leave(q0) ∨ ( sojourn(q0) ∧ ( step U ⋁_s A(s) ∧ X leave(s) ) )
    leave_parts = [leave(q0)]
    exit_after_anchor = _or([
        _F.And([f(A[s]), _F.X(leave(s))])
        for s in states if A[s] != buddy.bddfalse and leave(s) != _F.ff()
    ])
    if exit_after_anchor != _F.ff():
        leave_parts.append(_F.And([sojourn(q0), _F.U(step, exit_after_anchor)]))
    leave_branch = _or(leave_parts)

    return _F.Or([stay, leave_branch])
