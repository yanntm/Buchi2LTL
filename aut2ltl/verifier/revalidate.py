"""aut2ltl/verifier/revalidate.py — the boundary-crossing filter for NOT_LTL results.

A `NOT_LTL` verdict is only as good as the language it was certified on. When a
result crosses a language boundary — a decomposer recombining parts, a peeler
lifting a residue — the carried counting family described a *sub*-language, and
non-LTL-ness survives neither union, intersection, nor an inexact quotient. This
module is the enforcement of the lift rule
(`bls/definability/witness/algorithm.md`, Lifting): keep an absorbing `NOT_LTL`
only when its family **replays against the host language itself**; otherwise
degrade it to a non-absorbing decline carrying a `PROBABLY_NOT_LTL` diagnosis, so
no verdict is asserted and other translators stay free to answer.

Everything that is not a `NOT_LTL` passes through untouched.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from aut2ltl.result import LTLResult
from .check import verify

if TYPE_CHECKING:
    from aut2ltl.language import Language


def revalidated(res: "LTLResult", lang: "Language") -> "LTLResult":
    """Filter `res` at a language boundary: a `NOT_LTL` whose counting family is
    complete and replays (toggles with its period) against `lang`'s automaton is
    returned as-is — the verdict is valid for `lang` directly, independent of
    where the family was discovered. Anything else that claims `NOT_LTL` (no
    family, incomplete, failed replay, replay error) is degraded to a decline
    with a `PROBABLY_NOT_LTL` diagnosis, keeping the technique provenance. A
    non-`NOT_LTL` result passes through untouched."""
    if not res.not_ltl:
        return res
    witness = res.witness
    if witness is not None and witness.complete:
        try:
            ok, _pattern = verify(lang.tgba(), witness)
        except Exception:
            ok = False
        if ok:
            return res
    return LTLResult.decline(
        "PROBABLY_NOT_LTL -- a non-LTL verdict crossed a language boundary but "
        "its counting family does not certify against this language (the count "
        "may not survive the (de)composition), so no verdict is asserted",
        *res.technique,
    )


__all__ = ["revalidated"]
