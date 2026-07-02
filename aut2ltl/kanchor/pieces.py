"""The letter-level vocabulary of the graded read-off (algorithm.md).

Per-state LTL pieces built from the L/M/E guard data alone — window-width
independent: nothing here knows what k is. The assembler (`label.py`)
combines these under the triggers a level provides.

* `sojourn(s)` — `L(s) W M(s)`, the stay-then-move promise.
* `leave(s)`  — `L(s) U (exit now, child next)`, the stay-then-exit branch.
* `loop_forever(s)` — `G L(s)`, the parked tail (`None` when `s` has no loop).

Collapses: empty arms reduce the connectives (`false W m = m`,
`l W false = G l`, no exit = `false`), and — the tautology collapse —
`sojourn(s) ≡ ⊤` when `L(s) ∨ M(s) = true`: at each position either a loop
or a move is legal, so the weak until imposes nothing. The flag
`collapse=False` disables only the tautology collapse (the k = 1 label is
then byte-identical to `aut2ltl/anchor`'s, the regression rail).
"""

from typing import Dict, List, Optional, Tuple

import spot
import buddy

__all__ = ["Pieces"]

_F = spot.formula


class Pieces:
    """The per-state letter-level pieces of a component, from its guard data:
    `L`/`M` per-state BDDs, `exits` (`state → [(guard, dst)]`) and the child
    labels `phi` (`exit target → formula`). Holds the automaton's BDD dict for
    guard-to-formula conversion; stateless beyond its inputs."""

    def __init__(
        self, aut: "spot.twa_graph",
        L: Dict[int, "buddy.bdd"], M: Dict[int, "buddy.bdd"],
        exits: Dict[int, List[Tuple["buddy.bdd", int]]],
        phi: Dict[int, "spot.formula"],
        collapse: bool = True,
    ) -> None:
        self._d = aut.get_dict()
        self._L = L
        self._M = M
        self._exits = exits
        self._phi = phi
        self._collapse = collapse

    def f(self, bdd: "buddy.bdd") -> "spot.formula":
        """The guard as a propositional formula."""
        return spot.bdd_to_formula(bdd, self._d)

    def sojourn(self, s: int) -> "spot.formula":
        """`L(s) W M(s)` — loop at `s`, then move on (or park); collapsed when
        an arm is empty, `⊤` when the arms are exhaustive (see module doc)."""
        L, M = self._L[s], self._M[s]
        if self._collapse and (L | M) == buddy.bddtrue:
            return _F.tt()
        if L == buddy.bddfalse:
            return self.f(M)
        if M == buddy.bddfalse:
            return _F.G(self.f(L))
        return _F.W(self.f(L), self.f(M))

    def leave(self, s: int) -> "spot.formula":
        """`L(s) U (exit now, child next)`; `false` when `s` has no exit."""
        exit_or = _F.Or([
            _F.And([self.f(g), _F.X(self._phi[dst])])
            for g, dst in self._exits[s]
        ]) if self._exits[s] else _F.ff()
        if exit_or == _F.ff() or self._L[s] == buddy.bddfalse:
            return exit_or
        return _F.U(self.f(self._L[s]), exit_or)

    def loop_forever(self, s: int) -> Optional["spot.formula"]:
        """`G L(s)` — the parked tail; `None` when `s` has no self-loop."""
        if self._L[s] == buddy.bddfalse:
            return None
        return _F.G(self.f(self._L[s]))
