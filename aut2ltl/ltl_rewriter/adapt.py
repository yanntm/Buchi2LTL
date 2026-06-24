"""aut2ltl/ltl_rewriter/adapt.py — the boundary adapters (see algorithm.md).

The two — and only two — places `Language` / `Translator` meet the Rewriter world:

- `relabel(Λ)`        lifts a `Translator` INTO a `Rewriter` (the leaf that crosses to
                      automaton-land: re-describe the formula's language, re-label);
- `as_translator(s,R)` masquerades a `Rewriter` BACK AS a `Translator` for the
                      portfolio (seed with `s`, then rewrite with `R`).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from aut2ltl.language import Language, UntranslatableLanguage
from aut2ltl.result import LTLResult

if TYPE_CHECKING:
    from aut2ltl.translator import Translator
    from .rewriter import Rewriter


def relabel(labeler: "Translator") -> "Rewriter":
    """Lift a `Translator` into a `Rewriter`: re-describe `res.formula`'s language and
    re-label it with `labeler`, folding in `res`'s provenance. Declines when the
    labeler declines, or when the formula is too large for ltl2tgba
    (`UntranslatableLanguage`) — the one place a Rewriter decline originates."""
    def rewrite(res: "LTLResult") -> "LTLResult":
        try:
            out = labeler(Language.of_ltl(res.formula))
        except UntranslatableLanguage:
            return LTLResult.decline("relabel: untranslatable by ltl2tgba")
        return out.credit(res)
    return rewrite


def as_translator(seed: "Translator", rewriter: "Rewriter") -> "Translator":
    """Masquerade a `Rewriter` back as a `Translator`: label `L` with `seed` (the lone
    automaton → formula step, the only place `NOT_LTL` arises), then re-present the
    result with `rewriter`. A NOK seed propagates unchanged."""
    def translate(lang: "Language") -> "LTLResult":
        res = seed(lang)
        if res.nok:
            return res
        return rewriter(res)
    return translate
