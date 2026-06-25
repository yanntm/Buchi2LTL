"""The strength-decomposition composite Translator (see algorithm.md).

`StrengthDecompose(leaf)` splits a language by automaton **strength**: Spot's
strength decomposition (Renault et al., TACAS'13) cuts an automaton into its
weak / terminal / strong sub-automata, whose **union** is the language —
`L(A) = ⋃_{k ∈ {w,t,s}} L(decompose_scc(A,k))`, exact for *any* automaton (no
determinism needed). It is the `decompose` shape (`aut2ltl/decomp/decompose.py`)
with the strength `split` and a root ∨: recurse on each strength part (each is
single-strength and falls to the leaf), recombine with `Or`, delegate a
single-strength language (no split) to the leaf.
"""

from typing import List

import spot

from aut2ltl.combinators.decompose import decompose

_NAME = "strength"


def strength_pieces(aut: "spot.twa_graph") -> List["spot.twa_graph"]:
    """The weak / terminal / strong sub-automata of `aut` whose union is `L(aut)`
    (Spot's `decompose_scc`). Returns `[]` when the automaton is single-strength —
    the decomposition would just return the whole automaton, so there is no split."""
    si = spot.scc_info(aut)
    pieces: List["spot.twa_graph"] = []
    for keep in ("w", "t", "s"):
        try:
            sub = spot.decompose_scc(si, keep)
        except Exception:
            sub = None
        if sub is not None and sub.num_states() > 0:
            pieces.append(sub)
    # A genuine split needs at least two strengths present.
    return pieces if len(pieces) >= 2 else []


# Any form works — the union is exact on a nondeterministic automaton too — so the
# split queries the natural TGBA; no determinization is forced.
StrengthDecompose = decompose(
    lambda lang: strength_pieces(lang.tgba()), spot.formula.Or, _NAME)
