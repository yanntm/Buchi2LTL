"""aut2ltl/ltl_rewriter/adapt.py — the boundary adapters (see algorithm.md).

The two — and only two — places `Language` / `Translator` meet the Rewriter world:

- `relabel(Λ)`        lifts a `Translator` INTO a `Rewriter` (the leaf that crosses to
                      automaton-land: re-describe the formula's language, re-label);
- `as_translator(s,R)` masquerades a `Rewriter` BACK AS a `Translator` for the
                      portfolio (seed with `s`, then rewrite with `R`).
"""
from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from aut2ltl.language import Language, UntranslatableLanguage
from aut2ltl.result import LTLResult
from aut2ltl.printer import format_language, format_result

if TYPE_CHECKING:
    from aut2ltl.translator import Translator
    from .rewriter import Rewriter

# On when RELABEL_TRACE or the global TRANSLATOR_TRACE_ON is set (presence). Built
# only inside `if _TRACE:`.
_TRACE = "RELABEL_TRACE" in os.environ or "TRANSLATOR_TRACE_ON" in os.environ


class Relabel:
    """A Rewriter that re-describes `res.formula`'s language and re-labels it with a
    `Translator`, folding in `res`'s provenance. Declines when the labeler declines,
    or when the formula is untranslatable by ltl2tgba (`UntranslatableLanguage`).
    Returns `res` verbatim, uncredited, when the round trip reproduces the input
    formula (no-op ⇒ no credit). A named functor."""

    def __init__(self, labeler: "Translator") -> None:
        self._labeler = labeler
        self.name = f"relabel({getattr(labeler, 'name', type(labeler).__name__)})"

    def __call__(self, res: "LTLResult") -> "LTLResult":
        try:
            lang = Language.of_ltl(res.formula)
            if _TRACE:
                # relabel's real action: translate the input formula into a Language,
                # then label THAT. Show the crossing — the input result and the automaton
                # it becomes — so this language's id (the source of a re-presented
                # automaton) is attributable here. format_result is size-gated (no flatten).
                print("[relabel] in " + format_result(res) + "  -> language "
                      + format_language(lang, lang.tgba()), file=sys.stderr)
            out = self._labeler(lang)
        except UntranslatableLanguage:
            declined = LTLResult.decline("relabel: untranslatable by ltl2tgba")
            if _TRACE:
                print("[relabel] out " + format_result(declined), file=sys.stderr)
            return declined
        if out.ok and out.formula == res.formula:
            if _TRACE:
                print("[relabel] out no-op (round trip reproduced input)", file=sys.stderr)
            return res                  # round trip reproduced the formula → no-op, no credit
        result = out.credit(res)
        if _TRACE:
            print("[relabel] out " + format_result(result), file=sys.stderr)
        return result


def relabel(labeler: "Translator") -> "Rewriter":
    """The `Relabel` functor lifting `labeler` into a Rewriter."""
    return Relabel(labeler)


class AsTranslator:
    """A Translator that labels a `Language` to a formula with a seed `Translator`,
    then re-presents the result with a `Rewriter`. A NOK seed propagates unchanged.
    A named functor."""

    def __init__(self, seed: "Translator", rewriter: "Rewriter") -> None:
        self._seed = seed
        self._rewriter = rewriter
        self.name = (f"{getattr(seed, 'name', type(seed).__name__)}>>"
                     f"{getattr(rewriter, 'name', type(rewriter).__name__)}")

    def __call__(self, lang: "Language") -> "LTLResult":
        res = self._seed(lang)
        if res.nok:
            return res
        return self._rewriter(res)


def as_translator(seed: "Translator", rewriter: "Rewriter") -> "Translator":
    """The `AsTranslator` functor masquerading `rewriter` as a Translator seeded by
    `seed`."""
    return AsTranslator(seed, rewriter)
