"""The strength-decomposition composite Translator (see algorithm.md).

`StrengthDecompose(leaf)` splits a language by automaton **strength**: Spot's
strength decomposition (Renault et al., TACAS'13) cuts an automaton into its
weak / terminal / strong sub-automata, whose **union** is the language —
`L(A) = ⋃_{k ∈ {w,t,s}} L(decompose_scc(A,k))`, exact for *any* automaton (no
determinism needed). So it labels each strength part — recursing on itself, since a
part is single-strength and falls to the base case — and recombines with ∨,
delegating a single-strength language (no split) to the leaf.
"""

from typing import List, TYPE_CHECKING

import spot

from aut2ltl.language import Language
from aut2ltl.result import LTLResult, fuse
from aut2ltl.ltl.builders import own_simplify

if TYPE_CHECKING:
    from aut2ltl.contract import Translator

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


def _recombine(parts: List["LTLResult"]) -> "LTLResult":
    """Recombine the per-strength parts with a root ∨ via the accumulate idiom: seed
    an OK result tagged `strength<k>`, credit each part in (worst status wins,
    diagnoses accumulate), and bail if the fold is NOK — a declined part declines the
    whole. On OK, own-simplify the parts and their Or so cross-part folds and shared
    prefixes collapse (the Or is a node no per-part pass saw whole)."""
    res = fuse(LTLResult.start(f"{_NAME}{len(parts)}"), *parts)
    if res.nok:
        return res
    forms = [own_simplify(p.formula) for p in parts]
    res.formula = own_simplify(spot.formula.Or(forms))
    return res


class StrengthDecompose:
    """Strength decomposition as a Translator over a leaf Translator. Splits on ≥2
    strengths present (recursing on itself), else delegates the whole `Language` to
    the leaf. Transparent on technique: it adds `strength<k>` and forwards the parts'
    techniques."""

    name = _NAME

    def __init__(self, leaf: "Translator") -> None:
        self._leaf = leaf

    def __call__(self, lang: "Language") -> "LTLResult":
        # Any form works — the union is exact on a nondeterministic automaton too —
        # so query the natural TGBA; no determinization is forced here.
        pieces = strength_pieces(lang.tgba())
        if not pieces:
            return self._leaf(lang)               # single-strength: nothing to split
        return _recombine([self(Language.of(p)) for p in pieces])
