"""
bls/definability/gate.py — the LTL-definability gate, as a Translator decorator.

The kr cascade is *unsound on a non-LTL language*: the holonomy decomposition still
succeeds, but emits a group component the parser reads as a reset, yielding a wrong
formula. So a non-definable Language must be intercepted and reported as NOT_LTL
*before* the cascade builds. This module is that border — a decorator that wraps any
Translator and gates it on definability:

    safe = definability_gate(unsound_translator)

`definability_gate(inner)` returns a Translator that, on each Language, asks the
tester for the verdict and either:
  * **not definable** → builds the proper NOT_LTL `LTLResult` itself — the prose
    diagnosis (proof vs. strong-hint, per `conclusive`) and, knob-guarded, the
    non-LTL *witness* (the counting family certifying non-definability) — and returns
    it, short-circuiting the wrapped translator entirely; or
  * **definable** → delegates to `inner` (the cascade builds).

It is the single owner of "why not LTL": both the explanation and the witness. The
witness rides the `LTLResult` (beside the diagnosis) and travels up the portfolio by
`credit`; `aut2cas` stays a pure cascade adapter that never sees this concern.

LAYERING / dependencies. The gate orchestrates its two peer leaves — so neither
depends on the other:

    gate ──► tester  (label_ltl_definable: definable, conclusive)
         ──► witness (extract_witness: the Witness object)
         ──► floor   (LTLResult, Translator)

It imports neither `Cascade` nor `aut2cas`; it wraps an arbitrary `Translator`, so it
composes around the cascade adapter without a cycle.
"""

from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING

from aut2ltl.result import LTLResult
from aut2ltl.translator import Translator
from ..options import PRODUCE_WITNESS
from .tester import label_ltl_definable
from .witness import extract_witness

if TYPE_CHECKING:
    from aut2ltl.language import Language
    from aut2ltl.witness import Witness


def _produce_witness() -> bool:
    """Whether to extract a witness on the NOT_LTL branch (knob `kr.produce_witness`,
    default on). Read at the call site via env, like the tester's SAT-min threshold."""
    raw = os.environ.get(PRODUCE_WITNESS.env)
    return PRODUCE_WITNESS.default if raw is None else raw != "0"


def _explain(conclusive: bool) -> str:
    """The prose diagnosis for a non-aperiodic (NOT_LTL) language. When the verdict
    was read above the SAT-min threshold (`not conclusive`) the form may be
    non-minimal, so it is hedged as a strong hint rather than a proof."""
    qualifier = "" if conclusive else (
        "; the automaton was above the SAT-min threshold so it may be "
        "non-minimal — treat as a strong hint, not a proof"
    )
    return (
        "the deterministic transition monoid is non-aperiodic (carries a "
        "non-trivial group), so the language is not star-free / counter-free "
        "and no LTL formula exists" + qualifier
    )


def definability_gate(
    inner: Translator,
    *,
    gap_cmd: str = "gap",
    timeout: int = 180,
    max_aps: int = 5,
) -> Translator:
    """Wrap `inner` with the LTL-definability gate: report NOT_LTL (with diagnosis and,
    knob-guarded, a witness) on a non-definable Language, else delegate to `inner`.

    The verdict is cached on the Language (the downstream fail-safe), so this is the
    single choke point for all wrapped cascade members. The witness is best-effort: a
    failure to extract it never disturbs the (already decided) NOT_LTL verdict."""

    def gated(lang: "Language") -> LTLResult:
        definable, conclusive = label_ltl_definable(
            lang, gap_cmd=gap_cmd, timeout=timeout, max_aps=max_aps
        )
        if definable:
            return inner(lang)
        witness: Optional["Witness"] = None
        if _produce_witness():
            try:
                witness = extract_witness(
                    lang, complete=True, gap_cmd=gap_cmd, timeout=timeout, max_aps=max_aps
                )
            except Exception:
                witness = None  # best-effort: the verdict stands without a witness
        return LTLResult.not_definable(_explain(conclusive), witness=witness)

    return gated


__all__ = ["definability_gate"]
