"""The `sccdecomp` composite Translator (see algorithm.md).

`SccDecompose(leaf)` splits a language by the accepting SCCs of its automaton: the
per-SCC mark restriction A↾C makes `L(A↾C)` the words that lasso in C, and `L(A)`
is the union over accepting SCCs of these. So it labels each part — recursing on
itself, since A↾C has a single accepting SCC and falls to the base case — and
recombines with ∨, delegating an atomic part (≤1 accepting SCC) to the leaf. The
union is determinism-free and exact; the recombination declines if any part does.
"""

from typing import List, TYPE_CHECKING

import spot

from aut2ltl.language import Language
from aut2ltl.result import LTLResult, fuse
from aut2ltl.ltl.builders import own_simplify
from .restrict import accepting_sccs, ensure_marked, restrict_marks

if TYPE_CHECKING:
    from aut2ltl.contract import Translator

_NAME = "sccdecomp"


def _recombine(parts: List["LTLResult"]) -> "LTLResult":
    """Recombine the per-SCC parts with a root ∨ via the accumulate idiom: seed an
    OK result tagged `scc<k>`, credit each part in (worst status wins, diagnoses
    accumulate), and bail if the fold is NOK — a declined part declines the whole.
    On OK, own-simplify the parts and their Or so cross-part folds and shared
    prefixes collapse (the Or is a node no per-part pass saw whole)."""
    res = fuse(LTLResult.start(f"scc{len(parts)}"), *parts)
    if res.nok:
        return res
    forms = [own_simplify(p.formula) for p in parts]
    res.formula = own_simplify(spot.formula.Or(forms))
    return res


class SccDecompose:
    """Accepting-SCC decomposition as a Translator over a leaf Translator. Splits
    on ≥2 accepting SCCs (recursing on itself), else delegates the whole `Language`
    to the leaf. Transparent on technique: it adds `scc<k>` and forwards the parts'
    techniques."""

    name = _NAME

    def __init__(self, leaf: "Translator") -> None:
        self._leaf = leaf

    def __call__(self, lang: "Language") -> "LTLResult":
        # The right form: acceptance must be mark-based so that clearing marks
        # outside an SCC has meaning (`ensure_marked` materializes the all-accepting
        # `t` condition into Inf(0) over every edge).
        aut = ensure_marked(lang.tgba())
        accepting = accepting_sccs(aut)
        if len(accepting) < 2:
            return self._leaf(lang)               # atomic: nothing to split
        return _recombine([self(Language.of(restrict_marks(aut, C)))
                           for C in accepting])
