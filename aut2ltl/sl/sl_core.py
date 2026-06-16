"""Core sl ("self-loop") translator — the pure marguerite combinator.

Faithful implementation of the "Algorithm presentation" in `algorithm.md`. It
defines ONE class, `SlCore`, the higher-order Translator `sl(Λ)`: given a child
labeler `Λ` (any `Translator`) at construction, it labels a single **marguerite** —
the initial state of the input `Language`'s TGBA form — and delegates every exit to
`Λ`.

The mathematical content, for the initial state `q` with petals (self-loops) and
stems (exits `q → dst`):

    Final(q) = STAY∞(q) ∨ LEAVE(q)
    STAY∞(q) = G(σ) ∧ ⋀_{i<m} GF(σ_i)            -- stay forever, accepting
    LEAVE(q) = σ U ⋁_j ( g_j ∧ X φ_j )           -- stay finitely, then exit

with
    σ    = ⋁ { g : petal (g, A) }                -- all petal guards
    σ_i  = ⋁ { g : petal (g, A), i ∈ A }         -- petals carrying acc set i
    φ_j  = Λ( of(A↓dst_j) )                       -- the child label of stem j

and the accept/decline boundary: `q` is a marguerite iff its only incoming edges
are self-loops (`hasNonSelfIncoming`, necessary and sufficient, purely local). A
single declined child poisons `q`.

This module is deliberately minimal and PURE: no heuristics, no invariants, no
caching, no SCC machinery. The wiring (the `first`/`fix` combinators, dispatch,
memoization) belongs to a separate builder; this file is not meant to be edited
again as scenarios grow.

See `aut2ltl/sl/algorithm.md`.
"""

from typing import List, Tuple, TYPE_CHECKING

import spot

from aut2ltl.contract import LTLFormulaResult
from aut2ltl.language import Language

if TYPE_CHECKING:
    from aut2ltl.contract import Translator

_F = spot.formula
_TECH = {"sl"}


def _or(fs: List["spot.formula"]) -> "spot.formula":
    """Disjunction of `fs`; the empty disjunction is `false`."""
    return _F.Or(fs) if fs else _F.ff()


def _and(fs: List["spot.formula"]) -> "spot.formula":
    """Conjunction of `fs`; the empty conjunction is `true`."""
    return _F.And(fs) if fs else _F.tt()


def _has_non_self_incoming(aut: "spot.twa_graph", q: int) -> bool:
    """True iff some state other than `q` has an edge into `q` — the negation of
    "q is a marguerite". Necessary and sufficient (the automaton is reachable from
    its initial state), and purely local to `q`'s incoming edges."""
    for s in range(aut.num_states()):
        if s == q:
            continue  # self-loops are not "incoming" for the marguerite test
        for e in aut.out(s):
            if e.dst == q:
                return True
    return False


def _reroot(aut: "spot.twa_graph", state: int) -> "spot.twa_graph":
    """A fresh copy of `aut` rooted at `state` and trimmed to the states reachable
    from it — the sub-automaton `A↓state`, whose language is exactly what is
    accepted from `state`. Does not mutate `aut`."""
    sub = spot.automaton(aut.to_str("hoa"))
    sub.set_init_state(state)
    sub.purge_unreachable_states()
    return sub


class SlCore:
    """The pure sl combinator `sl(Λ)` as a `Translator` (`Language → LTLFormulaResult`).

    Constructed with the child labeler `Λ` it uses for exit targets (the decorator
    seam). It peels the initial state of the input Language's TGBA form when that
    state is a marguerite, and declines otherwise — see `algorithm.md`. Holds no
    state; create one per wiring (no instances are built here)."""

    def __init__(self, child: "Translator") -> None:
        self._child = child

    def __call__(self, lang: "Language") -> "LTLFormulaResult":
        aut = lang.tgba()
        q = aut.get_init_state_number()

        # Accept iff q is a marguerite (only self-loops come back to it).
        if _has_non_self_incoming(aut, q):
            return LTLFormulaResult.decline(_TECH)

        bdict = aut.get_dict()
        m = aut.acc().num_sets()

        # Partition q's out-edges into petals (self-loops) and stems (exits).
        petals: List[Tuple["spot.formula", frozenset]] = []   # (guard, acc sets)
        stems: List[Tuple["spot.formula", int]] = []          # (guard, dst)
        for e in aut.out(q):
            guard = spot.bdd_to_formula(e.cond, bdict)
            if e.dst == q:
                petals.append((guard, frozenset(e.acc.sets())))
            else:
                stems.append((guard, e.dst))

        # Delegate each stem to Λ on the re-rooted Language; one decline poisons q.
        # Credit the techniques of the children actually used (provenance on the
        # result envelope — the formula math is untouched).
        children: List["spot.formula"] = []
        tech = set(_TECH)
        for _, dst in stems:
            res = self._child(Language.of(_reroot(aut, dst)))
            if not res.ok:
                return LTLFormulaResult.decline(_TECH)
            children.append(res.formula)
            tech |= res.technique

        sigma = _or([g for g, _ in petals])

        # STAY∞(q) = G(σ) ∧ ⋀_{i<m} GF(σ_i)
        gfs = [_F.G(_F.F(_or([g for g, acc in petals if i in acc]))) for i in range(m)]
        stay = _and([_F.G(sigma)] + gfs)

        # LEAVE(q) = σ U ⋁_j ( g_j ∧ X φ_j )
        eps = _or([_F.And([g, _F.X(phi)]) for (g, _), phi in zip(stems, children)])
        leave = _F.U(sigma, eps)

        return LTLFormulaResult(_F.Or([stay, leave]), tech)
