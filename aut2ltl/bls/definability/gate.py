"""
bls/definability/gate.py — the LTL-definability gate, as a Translator decorator.

The kr cascade is *unsound on a non-LTL language*: the holonomy decomposition still
succeeds, but emits a group component the parser reads as a reset, yielding a wrong
formula. So a non-definable Language must be intercepted *before* the cascade builds.
This module is that border — a decorator that wraps any Translator and gates it on
definability:

    safe = definability_gate(unsound_translator)

The gate has THREE outcomes, not two (see README.md; the algebra is one-sided —
`tester/algorithm.md`, Soundness):

  * **aperiodic reading** → delegate to `inner` (a proof of LTL; the cascade builds);
  * **group + certified witness** → the absorbing `NOT_LTL`, carrying the counting
    family — a proof of non-LTL, independent of the algebra. *Certified* means the
    family is complete AND was replayed in-process against this Language's own
    automaton, toggling with the claimed period (`aut2ltl.verifier`);
  * **group + no certified witness** → a **non-absorbing decline** carrying a
    `PROBABLY_NOT_LTL` diagnosis: the group may be an encoding artefact
    (`gf_aa_parity`-class), so no verdict is asserted; `inner` is never called (the
    cascade stays fenced), but every other translator — each sound by construction —
    remains free to answer. A wrong absorbing rejection is thereby impossible.

The oracle failing to run at all (`definable=None`: extraction/GAP failure) takes
the same fence — a non-absorbing decline, `inner` never called — with its own
reason and no `PROBABLY_NOT_LTL` marker, since no group was read and no suspicion
exists. One behavior for everything the gate cannot certify: soundness holds by
construction, not by trusting that the cascade shares the oracle's failure mode.

With the witness knob off (`kr.produce_witness=0`) nothing can certify, so a group
reading always takes the decline branch: disabling witnesses disables absorbing
rejections, never soundness.

The suspect-branch work (GAP witness extraction + replay) is computed once per
Language and cached, since the gate wraps several portfolio rungs and an uncertified
decline lets the walk continue to the next gated arm.

LAYERING / dependencies. The gate orchestrates its leaves — none depends on another:

    gate ──► tester   (label_ltl_definable: definable, conclusive)
         ──► witness  (extract_witness: the Witness material)
         ──► replay   (aut2ltl.verifier.verify: in-process membership check)
         ──► floor    (LTLResult, Translator)

It imports neither `Cascade` nor `aut2cas`; it wraps an arbitrary `Translator`, so it
composes around the cascade adapter without a cycle.
"""

from __future__ import annotations

import os
import weakref
from typing import Optional, Tuple, TYPE_CHECKING

from aut2ltl.result import LTLResult
from aut2ltl.translator import Translator
from aut2ltl.verifier import verify
from ..options import PRODUCE_WITNESS
from .tester import label_ltl_definable
from .witness import extract_witness

if TYPE_CHECKING:
    from aut2ltl.language import Language
    from aut2ltl.witness import Witness


def _produce_witness() -> bool:
    """Whether to extract a witness on the suspect branch (knob `kr.produce_witness`,
    default on). Read at the call site via env, like the tester's SAT-min threshold."""
    raw = os.environ.get(PRODUCE_WITNESS.env)
    return PRODUCE_WITNESS.default if raw is None else raw != "0"


def _certified(witness: Optional["Witness"]) -> str:
    """The diagnosis of a certified rejection: the authority is the replayed family,
    not the algebraic reading that suggested it."""
    return (
        f"the language counts modulo {witness.p if witness else '?'}: a counting "
        f"family, certified by replay against the input, toggles membership with "
        f"n mod {witness.p if witness else '?'} — no counter-free LTL formula can "
        f"express this, so the language is not LTL-definable"
    )


def _suspicion(reason: str) -> str:
    """The diagnosis of an uncertified suspicion — a decline, never a verdict. The
    `PROBABLY_NOT_LTL` marker is load-bearing: reporting layers key on it."""
    return (
        "PROBABLY_NOT_LTL -- the deterministic transition monoid carries a "
        f"non-trivial group but {reason}; the group may be an encoding artefact "
        "of the deterministic form, so no verdict is asserted (the cascade is "
        "fenced; other translators may still answer)"
    )


# The suspect-branch outcome, once per Language: (witness material or None,
# certified?, reason when not certified).
_SUSPECT_CACHE: "weakref.WeakKeyDictionary[Language, Tuple[Optional[Witness], bool, str]]" \
    = weakref.WeakKeyDictionary()


def _certified_witness(
    lang: "Language", *, gap_cmd: str, timeout: int, max_aps: int
) -> Tuple[Optional["Witness"], bool, str]:
    """Extract the counting family for a suspect `lang` and replay it against the
    Language's own automaton. Returns `(witness, certified, reason)`: `certified`
    only when the family is complete and its membership pattern toggles with the
    claimed period on this input; otherwise `reason` says how far it got. Computed
    once per Language (cached) — fail-safe on any error (uncertified, never a
    verdict)."""
    try:
        return _SUSPECT_CACHE[lang]
    except KeyError:
        pass

    witness: Optional["Witness"] = None
    certified = False
    reason = "witness extraction is disabled"
    if _produce_witness():
        try:
            witness = extract_witness(
                lang, complete=True, gap_cmd=gap_cmd, timeout=timeout, max_aps=max_aps
            )
            if witness is None:
                reason = "no group element could be extracted"
            elif not witness.complete:
                reason = "no counting family completed (no phase-separating tail found)"
            else:
                ok, _pattern = verify(lang.tgba(), witness)
                certified = bool(ok)
                if not certified:
                    reason = "the completed family failed replay against the input"
        except Exception:
            witness, certified = None, False
            reason = "witness extraction or replay raised"

    outcome = (witness, certified, reason)
    _SUSPECT_CACHE[lang] = outcome
    return outcome


def definability_gate(
    inner: Translator,
    *,
    gap_cmd: str = "gap",
    timeout: int = 180,
    max_aps: int = 5,
) -> Translator:
    """Wrap `inner` with the LTL-definability gate: delegate on an aperiodic reading,
    report the absorbing `NOT_LTL` only on a certified witness, and decline (with a
    `PROBABLY_NOT_LTL` diagnosis, never calling `inner`) on an uncertified suspicion.

    The algebraic verdict is cached on the Language and the suspect-branch outcome in
    a per-Language cache, so this is a single choke point for all wrapped rungs."""

    def gated(lang: "Language") -> LTLResult:
        definable, _conclusive = label_ltl_definable(
            lang, gap_cmd=gap_cmd, timeout=timeout, max_aps=max_aps
        )
        if definable:
            return inner(lang)
        if definable is None:
            # The oracle could not run: nothing was read in either direction, so
            # the gate cannot vouch for the cascade — same fence as an uncertified
            # suspicion, but no suspicion is asserted (no group was read).
            return LTLResult.decline(
                "the definability oracle could not run (extraction or GAP "
                "failure), so definability is uncertified and the cascade is "
                "fenced; other translators may still answer", "gate",
            )
        witness, certified, reason = _certified_witness(
            lang, gap_cmd=gap_cmd, timeout=timeout, max_aps=max_aps
        )
        if certified:
            return LTLResult.not_definable(_certified(witness), "gate", witness=witness)
        return LTLResult.decline(_suspicion(reason), "gate")

    return gated


__all__ = ["definability_gate"]
