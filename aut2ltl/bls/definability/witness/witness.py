"""
bls/definability/witness/witness.py — extract non-LTL witness material.

`extract_witness(lang)` reads the same form as the definability gate
(`det_generic_minimal`, completed) and, on the non-aperiodic branch, returns the
period word `v` and period `p` of the counting family `(u, v, x, p)`: the group
element lifted to concrete letters, and its order. Stage 1 produces `(v, p)`;
`u` / `x` (completing the family) come later. See algorithm.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, TYPE_CHECKING

import spot

from aut2ltl.bls.extract import extract_generators
from aut2ltl.bls.gap.witness_group import witness_group

if TYPE_CHECKING:
    from aut2ltl.language import Language


@dataclass
class Witness:
    """Non-LTL witness material. `p` is the period (> 1); `v` is the period word,
    one concrete-letter string per step; `factor` is the 1-based generator-index
    word `v` lifts from (kept for checking the lift against the automaton)."""

    p: int
    v: List[str]
    factor: List[int]

    def v_str(self) -> str:
        return " ; ".join(self.v)


def _valuation_to_letter(val: Dict[str, bool]) -> str:
    """Render a letter valuation `{ap: bool}` as a Boolean cube, e.g. `a & !b`."""
    lits = [(ap if truth else f"!{ap}") for ap, truth in sorted(val.items())]
    return " & ".join(lits) if lits else "t"


def extract_witness(
    lang: "Language",
    *,
    gap_cmd: str = "gap",
    timeout: int = 60,
    max_aps: int = 5,
) -> Optional[Witness]:
    """Return the `(v, p)` witness material for a non-LTL `lang`, or `None` when the
    transition monoid carries no group (an aperiodic / LTL-definable language).

    Reads `det_generic_minimal()`, completes it, extracts the letter generators
    (keeping the valuations, unlike the gate), drives the witness GAP script, and
    lifts its factorization back to a word over concrete letters.
    """
    det = lang.det_generic_minimal()
    aut = spot.postprocess(det, "deterministic", "generic", "complete")
    gens, _masks, valuations = extract_generators(aut, max_aps=max_aps)
    raw = witness_group(gens, gap_cmd=gap_cmd, timeout=timeout)
    if raw is None:
        return None
    v = [_valuation_to_letter(valuations[i - 1]) for i in raw.factor]
    return Witness(p=raw.period, v=v, factor=list(raw.factor))


__all__ = ["Witness", "extract_witness"]
