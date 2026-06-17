"""The acceptance-conjunct decomposition composite Translator (see algorithm.md).

`AccDecompose(leaf)` splits a language by the top-level conjuncts of its acceptance
condition. On a **deterministic** automaton every word has a single run, so for a
conjunctive acceptance `acc = ⋀_i c_i` the language is the **intersection** of the
per-conjunct languages — `L(A) = ⋂_i L(A[acc := c_i])` — exact (on a
nondeterministic automaton the inclusion is strict). So it asks the Language for its
deterministic generic-minimal form (the determinism assumption is thus established
by the query, not assumed of the input), labels each per-conjunct part — recursing
on itself, since a part is single-condition and falls to the base case — and
recombines with ∧, delegating an atomic (non-conjunctive) acceptance to the leaf.
"""

from typing import List, TYPE_CHECKING

import spot

from aut2ltl.language import Language
from aut2ltl.result import LTLResult, fuse
from aut2ltl.ltl.builders import own_simplify

if TYPE_CHECKING:
    from aut2ltl.contract import Translator

_NAME = "acc"


def conjunct_pieces(aut: "spot.twa_graph") -> List["spot.twa_graph"]:
    """One single-condition sub-automaton per top-level acceptance conjunct of `aut`
    (same structure, acceptance restricted to that conjunct, then cleaned). Returns
    `[]` when the acceptance is not a conjunction of ≥2 — there is no AND split."""
    conj = aut.acc().get_acceptance().top_conjuncts()
    if len(conj) < 2:
        return []
    pieces: List["spot.twa_graph"] = []
    for c in conj:
        sub = spot.automaton(aut.to_str("hoa"))    # independent clone
        sub.set_acceptance(spot.acc_cond(aut.num_sets(), c))
        spot.cleanup_acceptance_here(sub)
        pieces.append(sub)
    return pieces


def _recombine(parts: List["LTLResult"]) -> "LTLResult":
    """Recombine the per-conjunct parts with a root ∧ via the accumulate idiom: seed
    an OK result tagged `acc<k>`, credit each part in (worst status wins, diagnoses
    accumulate), and bail if the fold is NOK — a declined part declines the whole. On
    OK, own-simplify the parts and their And so cross-part folds and shared prefixes
    collapse (the And is a node no per-part pass saw whole)."""
    res = fuse(LTLResult.start(f"{_NAME}{len(parts)}"), *parts)
    if res.nok:
        return res
    forms = [own_simplify(p.formula) for p in parts]
    res.formula = own_simplify(spot.formula.And(forms))
    return res


class AccDecompose:
    """Acceptance-conjunct decomposition as a Translator over a leaf Translator.
    Splits a deterministic automaton on ≥2 acceptance conjuncts (recursing on
    itself), else delegates the whole `Language` to the leaf. Transparent on
    technique: it adds `acc<k>` and forwards the parts' techniques."""

    name = _NAME

    def __init__(self, leaf: "Translator") -> None:
        self._leaf = leaf

    def __call__(self, lang: "Language") -> "LTLResult":
        # Deterministic (the AND-split precondition), generic (keeps the conjunctive
        # ⋀Inf / Streett acceptance shape instead of collapsing to parity), and
        # state-minimal. Determinism is guaranteed by the form we ask for, never of
        # the input.
        pieces = conjunct_pieces(lang.det_generic_minimal())
        if not pieces:
            return self._leaf(lang)               # atomic acceptance: nothing to split
        return _recombine([self(Language.of(p)) for p in pieces])
