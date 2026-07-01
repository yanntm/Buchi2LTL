"""
aut2ltl/best_of/best_of.py — the choice-by-size combinator.

`best_of` is the size-objective sibling of `first_success`: where `first_success`
takes the FIRST language-faithful stage (choice by cited order), `best_of` walks the
stages IN ORDER keeping the first as the trusted incumbent and lets a later stage
take over only when a pluggable `beats` comparator says it wins. Both obey the same
contract — every stage is language-faithful or DECLINED — so the winner is sound by
construction whichever one is chosen.

The whole policy lives in ONE place: a `Comparator` (`beats(incumbent, challenger) ->
bool`, see `comparators.py`), a comparison of two full `LTLResult`s. That is the
single pluggable seam — swap it to change what "better form" means (size, a
significance margin, temporals-first, technique preference, …) without touching the
walk. The default `smaller` is strict-min on DAG-node size; `significantly_smaller`
is the *guidance* policy: the first-cited answer is trusted (expected at least as good
on grounds the metric cannot see — factoring, readability) and is overridden only on
a win large enough to trust it.
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Generic, Optional, Sequence, TypeVar

from aut2ltl.result import LTLResult
from aut2ltl.printer import format_language, format_result
from .comparators import Comparator, smaller

_In = TypeVar("_In")

# On when BEST_OF_TRACE or the global TRANSLATOR_TRACE_ON is set (presence). Built
# only inside `if _TRACE:`. Shows the size choice: each candidate and whether a
# challenger beats the incumbent.
_TRACE = "BEST_OF_TRACE" in os.environ or "TRANSLATOR_TRACE_ON" in os.environ


def _stage_name(stage: object) -> str:
    return getattr(stage, "name", type(stage).__name__)


class _BestOf(Generic[_In]):
    """The choice-by-size composite as a real, named translator: it obeys the
    Translator / CascadeTranslator interface (a fixed `name` plus a `__call__`), so
    a composite is itself a valid stage of another composite.

    Each stage is self-gating (a stage that does not apply returns DECLINED). The
    stages are walked IN ORDER: the first OK is the incumbent, and a later OK replaces
    it only when `beats(incumbent, challenger)`. The winner is returned UNCHANGED (the
    composite stamps no tag of its own; its `name` is its identity, not a technique).
    A NOT_LTL from any stage short-circuits: the language is not LTL-definable, so no
    stage can produce a faithful formula and the verdict stands.
    """

    def __init__(
        self,
        name: str,
        stages: Sequence[Callable[[_In], LTLResult]],
        beats: Comparator,
    ) -> None:
        self.name = name
        self._stages = tuple(stages)
        self._beats = beats

    def __call__(self, x: _In) -> LTLResult:
        if _TRACE:
            if hasattr(x, "tgba"):                 # a Language input
                print(f"[best_of:{self.name}] in " + format_language(x, x.tgba()),
                      file=sys.stderr)
            elif isinstance(x, LTLResult):         # a rewriter-mode input (a result to re-present)
                print(f"[best_of:{self.name}] in " + format_result(x), file=sys.stderr)
        incumbent: Optional[LTLResult] = None
        winner: Optional[str] = None
        for stage in self._stages:
            name = _stage_name(stage)
            r = stage(x)                          # the delegation
            if r.not_ltl:
                if _TRACE:
                    print(f"[best_of:{self.name}] {name} -> NOT_LTL (short-circuit) "
                          + format_result(r), file=sys.stderr)
                return r                          # absorbing verdict: keep reason
            if r.declined:
                if _TRACE:
                    print(f"[best_of:{self.name}] {name} -> declined "
                          + format_result(r), file=sys.stderr)
                continue                          # not this stage's case: move on
            if incumbent is None:
                incumbent, winner = r, name       # the trusted first answer
                verb = "incumbent"
            elif self._beats(incumbent, r):
                incumbent, winner = r, name       # a winning challenger takes over
                verb = "WINS"
            else:
                verb = "kept out"                 # challenger not better: incumbent stands
            if _TRACE:
                print(f"[best_of:{self.name}] {name} -> {verb} " + format_result(r),
                      file=sys.stderr)
        result = incumbent if incumbent is not None else LTLResult.decline()
        if _TRACE:
            print(f"[best_of:{self.name}] out (winner={winner or 'none'}) "
                  + format_result(result), file=sys.stderr)
        return result


def best_of(
    stages: Sequence[Callable[[_In], LTLResult]],
    *,
    name: str = "best_of",
    beats: Comparator = smaller,
) -> "_BestOf[_In]":
    """Compose `stages` into a single named translator that walks them in order and
    returns the trusted-incumbent winner: the first OK stage, overridden by a later
    OK only when `beats(incumbent, challenger)` (default `smaller`: strict-min size).
    A NOT_LTL verdict from any stage is returned at once; a DECLINE if every stage
    declines. `name` is the composite's identity (passed at construction)."""
    return _BestOf(name, stages, beats)
