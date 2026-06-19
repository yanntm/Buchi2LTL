"""The accepting-SCC decomposition composite Translator (see algorithm.md).

`SccDecompose(leaf)` splits a language by the accepting SCCs of its automaton: the
per-SCC mark restriction A↾C makes `L(A↾C)` the words that lasso in C, and `L(A)`
is the union over accepting SCCs of these. It is the `decompose` shape
(`aut2ltl/decomp/decompose.py`) with the accepting-SCC `split` and a root ∨: recurse
on each part (A↾C has a single accepting SCC and falls to the leaf), recombine with
`Or`, delegate an atomic part (≤1 accepting SCC) to the leaf. The union is
determinism-free and exact.
"""

from typing import List, TYPE_CHECKING

import spot

from aut2ltl.decomp.decompose import decompose
from .restrict import accepting_sccs, ensure_marked, restrict_marks

if TYPE_CHECKING:
    from aut2ltl.language import Language

_NAME = "scc"


def _split(lang: "Language") -> List["spot.twa_graph"]:
    """The per-accepting-SCC mark restrictions A↾C, or `[]` when there is ≤1 accepting
    SCC (nothing to split). Acceptance is first made mark-based (`ensure_marked`) so
    that clearing marks outside an SCC has meaning."""
    aut = ensure_marked(lang.tgba())
    accepting = accepting_sccs(aut)
    if len(accepting) < 2:
        return []
    return [restrict_marks(aut, C) for C in accepting]


SccDecompose = decompose(_split, spot.formula.Or, _NAME)
