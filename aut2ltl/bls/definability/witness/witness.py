"""
bls/definability/witness/witness.py — extract non-LTL witness material.

`extract_witness(lang)` reads the same form as the definability tester
(`det_generic_minimal`, completed), drives the witness GAP script to obtain a
non-trivial group element of the transition monoid (period `p > 1`) lifted to a
concrete letter word `v`, then tries to COMPLETE a counting family on the
automaton: the linear shape first (`linear.complete_linear` — all orbits, all
phase pairs), the ω-power shape when no tail separates (`omega.complete_omega`
— enriched-monoid candidates). The returned `Witness` may still be incomplete:
completion failure after both shapes is the caller's abstention signal, not an
error. See algorithm.md.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import spot

from aut2ltl.witness import Witness
from aut2ltl.bls.extract import extract_generators
from aut2ltl.bls.gap.witness_group import witness_group
from .linear import complete_linear
from .omega import complete_omega
# Compat re-exports: probes (witness/pin.py) ground the GAP lift on these.
from .support import induced_transform as _induced_transform          # noqa: F401
from .support import valuation_to_letter as _valuation_to_letter

if TYPE_CHECKING:
    from aut2ltl.language import Language


def extract_witness(
    lang: "Language",
    *,
    complete: bool = False,
    gap_cmd: str = "gap",
    timeout: int = 60,
    max_aps: int = 5,
) -> Optional[Witness]:
    """Return the witness material for a suspect `lang`, or `None` when the
    transition monoid carries no group (an aperiodic / LTL-definable language).

    Reads `det_generic_minimal()`, completes it, extracts the letter generators
    (keeping the valuations, unlike the tester), drives the witness GAP script,
    and lifts its factorization back to the period word `v`. With
    `complete=True` it also synthesises the family completion — linear
    `(u, x)`, else ω-power `(u, y)` — best-effort: an incomplete return means
    neither shape completed within bounds."""
    det = lang.det_generic_minimal()
    aut = spot.postprocess(det, "deterministic", "generic", "complete")
    gens, _masks, valuations = extract_generators(aut, max_aps=max_aps)
    raw = witness_group(gens, gap_cmd=gap_cmd, timeout=timeout)
    if raw is None:
        return None
    v = [_valuation_to_letter(valuations[i - 1]) for i in raw.factor]
    w = Witness(p=raw.period, v=v, factor=list(raw.factor))
    if complete:
        if not complete_linear(w, aut, gens, valuations):
            complete_omega(w, aut, gens, valuations)
    return w


__all__ = ["extract_witness"]
