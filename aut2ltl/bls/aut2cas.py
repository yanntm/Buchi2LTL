"""
kr/aut2cas.py — lift a CascadeTranslator up to a Translator via the GAP bridge.

A CascadeTranslator works on an already-decomposed `Cascade`; a `Translator`
works on a contract `Language` (the floor input type). `as_translator` is the
adapter that closes the gap: given a Language it builds the Krohn-Rhodes cascade
with `decompose_lang` (pulls `Language.det_parity_sbacc()` -> GAP SgpDec holonomy)
and runs the cascade-translator on it. The result `LTLResult` (formula +
technique) is forwarded unchanged.

Before building, it runs the LTL-definability gate (`kr/ltl_tester`): the cascade
is unsound on a non-aperiodic language, so a non-definable Language is reported as
NOT_LTL (cached on the Language) instead of built — skipping the explosive
holonomy step entirely on the non-LTL case.

The module builds the default endpoint singleton `reconstruct`
(= `as_translator(hierarchy_class)`): the pure-kr Language -> LTLResult
entry, the cascade-level construction lifted to the Language level.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from aut2ltl.translator import Translator
from .cascade_translator import CascadeTranslator
from aut2ltl.result import LTLResult
from .gap import decompose_lang
from .cascade import CascadeHolder
from .hierarchy_class import hierarchy_class
from .ltl_tester import label_ltl_definable

if TYPE_CHECKING:
    from aut2ltl.language import Language


def as_translator(
    ct: CascadeTranslator,
    *,
    gap_cmd: str = "gap",
    timeout: int = 180,
    max_aps: int = 5,
) -> Translator:
    """Lift a CascadeTranslator to a Translator: decompose the Language to a
    cascade (GAP) and run `ct` on it. Decomposition options are captured at build
    time; the returned Translator takes only the Language (the contract shape)."""

    def reconstruct(lang: "Language") -> LTLResult:
        # LTL-DEFINABILITY GATE (BEFORE the explosive holonomy build). The cascade
        # is UNSOUND on a non-aperiodic language: the holonomy decomposition still
        # succeeds, but it emits a GROUP component the parser labels a reset, from
        # which the members build a WRONG formula (the kinská counting cases). The
        # oracle runs on a sbacc-FREE form (kr/ltl_tester.py — the cascade's own
        # parity+sbacc D degeneralizes generalized-Büchi acceptance into a spurious
        # counter that reads as non-aperiodic even for LTL languages), is cached on
        # the Language, and is the one choke point for ALL cascade members (they
        # each run only after this). On a non-definable reading we report the
        # impossibility instead of building; `conclusive` iff the verdict was read
        # on a state-minimal automaton.
        definable, conclusive = label_ltl_definable(
            lang, gap_cmd=gap_cmd, timeout=timeout, max_aps=max_aps
        )
        if not definable:
            qualifier = "" if conclusive else (
                "; the automaton was above the SAT-min threshold so it may be "
                "non-minimal — treat as a strong hint, not a proof"
            )
            note = (
                "the deterministic transition monoid is non-aperiodic (carries a "
                "non-trivial group), so the language is not star-free / counter-free "
                "and no LTL formula exists" + qualifier
            )
            return LTLResult.not_definable(diagnosis=note)
        casc = decompose_lang(lang, gap_cmd=gap_cmd, timeout=timeout, max_aps=max_aps)
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
        # The CascadeHolder carries this build's memos + counters (no module
        # globals, no reset); discarding it after the build IS the reset.
        holder = CascadeHolder(casc)
        return ct(holder)

    return reconstruct


reconstruct: Translator = as_translator(hierarchy_class)


__all__ = ["as_translator", "reconstruct"]
