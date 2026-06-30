"""aut2ltl/recurse/recurse.py — the recursive-descent brick (`recurse`).

The structural-recursion combinator that complements `first_success`: where that
one is *choice* (a flat chain of distinct translators), this one is
*self-reference* (a translator that contains itself). See the package README.
"""
from __future__ import annotations

import os
import sys
from typing import Callable, TYPE_CHECKING

from aut2ltl.printer import format_language

if TYPE_CHECKING:
    from aut2ltl.language import Language
    from aut2ltl.result import LTLResult
    from aut2ltl.translator import Translator

# On when RECURSE_TRACE or the global TRANSLATOR_TRACE_ON is set (presence). Built
# only inside `if _TRACE:`. Shows each level of the descent — the language re-entered
# at every recursion step, so a delegated sub-language can be followed down.
_TRACE = "RECURSE_TRACE" in os.environ or "TRANSLATOR_TRACE_ON" in os.environ


class _Recurse:
    """The recursive-descent fixpoint as a functor: `leaf = step(leaf)`. `__call__`
    builds the one-level translator `step(self)` — passing `self` as the recursion
    target so `step` may delegate sub-problems back to it — and runs it on the input.
    Adds no base case and no behaviour of its own. A named functor.

    `step` must be a one-level decorator with a well-founded descent (it delegates
    only strictly-smaller sub-problems to the target); termination rests on that.
    Soundness is inherited from the Translator contract (every value that flows is a
    language-faithful or declined `LTLResult`, never wrong)."""

    def __init__(self, step: "Callable[[Translator], Translator]", name: str) -> None:
        self._step = step
        self.name = name

    def __call__(self, lang: "Language") -> "LTLResult":
        if _TRACE:
            print("[recurse] descend " + format_language(lang, lang.tgba()),
                  file=sys.stderr)
        return self._step(self)(lang)


def recurse(step: "Callable[[Translator], Translator]", *,
            name: str = "recurse") -> "Translator":
    """The `_Recurse` fixpoint of `step` (`leaf = step(leaf)`)."""
    return _Recurse(step, name)
