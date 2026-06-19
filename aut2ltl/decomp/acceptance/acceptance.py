"""The acceptance-conjunct decomposition composite Translator (see algorithm.md).

`AccDecompose(leaf)` splits a language by the top-level conjuncts of its acceptance
condition. On a **deterministic** automaton every word has a single run, so for a
conjunctive acceptance `acc = ⋀_i c_i` the language is the **intersection** of the
per-conjunct languages — `L(A) = ⋂_i L(A[acc := c_i])` — exact (on a
nondeterministic automaton the inclusion is strict). It is the `decompose` shape
(`aut2ltl/decomp/decompose.py`) with the conjunct `split` over the deterministic
generic-minimal form (so the determinism precondition is established by the query,
not assumed) and a root ∧: recurse on each single-condition part, recombine with
`And`, delegate an atomic (non-conjunctive) acceptance to the leaf.
"""

from typing import List

import spot

from aut2ltl.decomp.decompose import decompose

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


# Deterministic (the AND-split precondition), generic (keeps the conjunctive ⋀Inf /
# Streett shape instead of collapsing to parity), state-minimal — the form is asked
# for, never assumed of the input.
AccDecompose = decompose(
    lambda lang: conjunct_pieces(lang.det_generic_minimal()), spot.formula.And, _NAME)
