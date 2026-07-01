"""
bls/definability/witness/reseed.py — re-complete a crossed family on a new host.

A counting family certified for a sub-language can fail on the composed host even
when the host is genuinely non-LTL: the composition masks the certificate's toggle
(both parts of an intersection can count while neither family survives whole). The
verdict is then recoverable **without GAP** — GAP's only contribution was the group
element, and its period word `v` survives the crossing as concrete letters.
`reseed_witness(w, host)` re-expresses `v` over the host's own deterministic form
(one consistent concretization per cube letter) and runs the same
linear-then-ω-power completion there. The result is a first-class host certificate —
same concrete closure, same replay obligation — or `None` when nothing completes
within bounds. Fail-safe: any error is `None`, never a verdict.
"""
from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

import buddy
import spot

from aut2ltl.witness import Witness
from aut2ltl.bls.extract import extract_generators
from .linear import complete_linear
from .omega import complete_omega
from .support import valuation_to_letter

if TYPE_CHECKING:
    from aut2ltl.language import Language


def _letter_index(
    letter: str, valuations: List[Dict[str, bool]], aut: "spot.twa_graph"
) -> Optional[int]:
    """The first host letter (valuation index) consistent with the crossed cube
    `letter` — the concretization used to re-express `v` on the host — or `None`
    when no host letter satisfies it."""
    d = aut.get_dict()
    lb = spot.formula_to_bdd(spot.formula(letter), d, aut)
    for i, val in enumerate(valuations):
        vb = spot.formula_to_bdd(spot.formula(valuation_to_letter(val)), d, aut)
        if (lb & vb) != buddy.bddfalse:
            return i
    return None


def reseed_witness(
    w: "Witness", host: "Language", *, max_aps: int = 5
) -> Optional["Witness"]:
    """A counting family for `host`, completed from the crossed family's period
    word `v`: map each letter of `v` to a host generator, then complete the linear
    shape (all cycles × all phase pairs) and, failing that, the ω-power shape on
    the host's completed `det_generic_minimal()` form. `None` when `v` does not
    re-express, nothing completes, or anything errors."""
    try:
        det = host.det_generic_minimal()
        aut = spot.postprocess(det, "deterministic", "generic", "complete")
        gens, _masks, valuations = extract_generators(aut, max_aps=max_aps)
        factor: List[int] = []
        for letter in w.v:
            i = _letter_index(letter, valuations, aut)
            if i is None:
                return None
            factor.append(i + 1)
        w2 = Witness(p=w.p,
                     v=[valuation_to_letter(valuations[i - 1]) for i in factor],
                     factor=factor)
        if not complete_linear(w2, aut, gens, valuations):
            complete_omega(w2, aut, gens, valuations)
        return w2 if w2.complete else None
    except Exception:
        return None


__all__ = ["reseed_witness"]
