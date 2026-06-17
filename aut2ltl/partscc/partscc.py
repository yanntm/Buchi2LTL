"""The `partscc` leaf Translator (see algorithm.md).

`PartScc` labels a Language whose TGBA is a single terminal (escape-free) SCC by
partitioning it: each state gets a uniquely-characterizing label `L(s)`, and when
the labels are tight and pairwise disjoint it emits `φ = G(⋁ L(s) ∧ X O(s))`,
adopted **only** if it is language-equivalent to the component. Otherwise it
declines. Self-contained: no child, no composer cooperation, no entry-timing — the
input *is* the whole "stay forever" language, so the steady-state `φ` is the whole
answer.
"""

from typing import TYPE_CHECKING

import spot

from aut2ltl.language import Language
from aut2ltl.result import LTLResult
from .labels import scc_states, partition, outgoing_or

if TYPE_CHECKING:  # spot imported above for runtime use
    pass

_NAME = "partscc"
_F = spot.formula


def _validates(aut: "spot.twa_graph", phi: "spot.formula") -> bool:
    """Soundness gate: `φ` is adopted only if it is language-equivalent to the
    component `aut`. A wrong partition guess simply fails here and is declined, so
    partscc can never answer unsoundly."""
    try:
        cand = phi.translate("GeneralizedBuchi", "Small", "High")
        return spot.are_equivalent(aut, cand)
    except Exception:
        return False


class PartScc:
    """The terminal-SCC partition as a leaf `Translator` (`Language → LTLResult`).

    A producer, not a decorator: it takes no child and holds no state."""

    name = _NAME

    def __call__(self, lang: "Language") -> "LTLResult":
        aut = lang.tgba()

        states = scc_states(aut)
        if states is None:
            return LTLResult.decline("not a single SCC of size >= 2")

        labels = partition(aut, states)
        if labels is None:
            return LTLResult.decline(
                "L-labels are not a tight pairwise-disjoint partition")

        # The L-partition makes the SCC deterministic (a letter σ leads to the
        # unique state with σ ∈ L(s)), so the language from the init state q0 is
        #     O(q0)  ∧  G( ⋀_s ( L(s) → X O(s) ) )
        # The G-part is the steady-state transition law (if the last letter put us
        # in s, the next is a valid move out of s); the O(q0) conjunct anchors
        # position 0 to the init state's own outgoing availability — there is no
        # incoming letter there, which is exactly the entry phase a bare steady G
        # over-approximates.
        d = aut.get_dict()

        def _f(bdd: "buddy.bdd") -> "spot.formula":
            return spot.bdd_to_formula(bdd, d)

        steady = _F.G(_F.And([
            _F.Or([_F.Not(_f(labels[s])), _F.X(_f(outgoing_or(aut, s)))])
            for s in states
        ]))
        anchor = _f(outgoing_or(aut, aut.get_init_state_number()))
        phi = _F.And([anchor, steady])

        if not _validates(aut, phi):
            return LTLResult.decline(
                "candidate not language-equivalent to the component")

        return LTLResult.success(phi, _NAME)
