"""
kr/aut2cas.py — lift a CascadeTranslator up to a Translator via the GAP bridge.

A CascadeTranslator works on an already-decomposed `Cascade`; a `Translator`
(the twa-level contract) works on a raw automaton. `as_translator` is the adapter
that closes the gap: given an automaton it builds the Krohn-Rhodes cascade with
`decompose_aut` (Spot normalization to deterministic parity + GAP SgpDec
holonomy) and runs the cascade-translator on it. The result `ReconResult`
(formula + technique) is forwarded unchanged.

The module builds the default endpoint singleton `reconstruct`
(= `as_translator(hierarchy_class)`): the pure-kr twa -> ReconResult entry, the
cascade-level construction lifted to the automaton level.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from aut2ltl.contract import ReconResult, Translator, CascadeTranslator
from .gap import decompose_aut
from .hierarchy_class import hierarchy_class

if TYPE_CHECKING:
    import spot


def as_translator(
    ct: CascadeTranslator,
    *,
    gap_cmd: str = "gap",
    timeout: int = 180,
    max_aps: int = 5,
) -> Translator:
    """Lift a CascadeTranslator to a Translator: decompose the automaton to a
    cascade (GAP) and run `ct` on it. Decomposition options are captured at build
    time; the returned Translator takes only the automaton (the contract shape)."""

    def reconstruct(twa: "spot.twa_graph") -> ReconResult:
        casc = decompose_aut(twa, gap_cmd=gap_cmd, timeout=timeout, max_aps=max_aps)
        # Depth guard dropped (was 3 levels during find-issues-small-first dev):
        # the ladder is green through 3L and the construction is fully memoized
        # with a distinct-subproblem guard (KR_REACH_GUARD), which is the real
        # runaway protection. KR_MAX_LEVELS gives an opt-in ceiling if ever needed.
        max_levels = int(os.environ.get("KR_MAX_LEVELS", "0"))
        if max_levels > 0 and casc.num_levels > max_levels:
            raise NotImplementedError(
                f"Reconstruction depth ceiling KR_MAX_LEVELS={max_levels} "
                f"(got {casc.num_levels} levels)."
            )
        return ct(casc)

    return reconstruct


reconstruct: Translator = as_translator(hierarchy_class)


__all__ = ["as_translator", "reconstruct"]
