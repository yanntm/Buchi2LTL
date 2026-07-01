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

from typing import Callable, List, Optional, TYPE_CHECKING

from aut2ltl.result import LTLResult
from .check import member, verify_with

if TYPE_CHECKING:
    from aut2ltl.language import Language
    from aut2ltl.witness import Witness

# Engine-side recovery hook: complete a fresh family for the host from a crossed
# family's group element (see bls/definability/witness/reseed.py).
Reseed = Callable[["Witness", "Language"], "Optional[Witness]"]


def _degraded(res: "LTLResult") -> "LTLResult":
    """The non-absorbing decline a failed crossing degrades to (provenance kept)."""
    return LTLResult.decline(
        "PROBABLY_NOT_LTL -- a non-LTL verdict crossed a language boundary but "
        "its counting family does not certify against this language (the count "
        "may not survive the (de)composition), so no verdict is asserted",
        *res.technique,
    )


def _filtered(
    res: "LTLResult", member_of: "Callable[[str], bool]"
) -> "LTLResult":
    """Keep a `NOT_LTL` only if its complete family replays through `member_of`;
    degrade anything else claiming `NOT_LTL`; pass every other result through."""
    if not res.not_ltl:
        return res
    witness = res.witness
    if witness is not None and witness.complete:
        try:
            ok, _pattern = verify_with(member_of, witness)
        except Exception:
            ok = False
        if ok:
            return res
    return _degraded(res)


def revalidated(res: "LTLResult", lang: "Language") -> "LTLResult":
    """Filter `res` at a language boundary: a `NOT_LTL` whose counting family is
    complete and replays (toggles with its period) against `lang`'s automaton is
    returned as-is — the verdict is valid for `lang` directly, independent of
    where the family was discovered. Anything else that claims `NOT_LTL` (no
    family, incomplete, failed replay, replay error) is degraded to a decline
    with a `PROBABLY_NOT_LTL` diagnosis, keeping the technique provenance. A
    non-`NOT_LTL` result passes through untouched."""
    return _filtered(res, lambda word: member(lang.tgba(), word))


def revalidated_by_parts(
    res: "LTLResult",
    parts: List["Language"],
    conjunctive: bool,
    *,
    host: "Optional[Language]" = None,
    reseed: "Optional[Reseed]" = None,
) -> "LTLResult":
    """`revalidated` for a host whose language is the conjunction (`∧`) or
    disjunction (`∨`) of `parts` — a faithful split, so membership of any word in
    the host IS the connective of its memberships in the parts. The replay runs
    part-sized queries only; no host product or determinization is ever built.

    Optional recovery: when the crossed family fails and a `reseed` callable is
    injected (engine-side, `reseed(witness, host) -> Optional[Witness]`), a fresh
    family completed for `host` from the crossed group element is tried and — if
    it replays through the same parts — asserted as this level's certified
    `NOT_LTL` (provenance kept). Nothing certifies ⇒ the degraded decline."""
    if not res.not_ltl:
        return res
    combine = all if conjunctive else any

    def member_of(word: str) -> bool:
        return combine(member(p.tgba(), word) for p in parts)

    kept = _filtered(res, member_of)
    if kept.not_ltl or reseed is None or host is None or res.witness is None:
        return kept
    try:
        w2 = reseed(res.witness, host)
        if w2 is not None and w2.complete:
            ok, _pattern = verify_with(member_of, w2)
            if ok:
                return LTLResult.not_definable(
                    f"the language counts modulo {w2.p}: a counting family "
                    "reseeded from a crossed verdict's group element, certified "
                    "by replay through the split parts — no counter-free LTL "
                    "formula can express this, so the language is not "
                    "LTL-definable",
                    *res.technique, witness=w2,
                )
    except Exception:
        pass
    return kept


__all__ = ["revalidated", "revalidated_by_parts"]
