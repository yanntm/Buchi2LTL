"""
aut2ltl/first_success.py — composite translators built over the contract.

A composite is itself a translator: it delegates to a collection of
sub-translators and combines their `LTLResult`s. Because every sub-result obeys
the contract invariant (language-faithful or DECLINED, never wrong), the
composite is sound by construction. The combinators here are generic over the
input type, so they apply to both `Translator` (automaton in) and
`CascadeTranslator` (cascade in) stages.

`first_success` is the chain-of-responsibility composite: try the stages in
order, take the first language-faithful result, else decline. The kr
acceptance-dispatch chain (acc → weak → buchi → cobuchi → bls) is one such
composition.
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Generic, Sequence, TypeVar

from aut2ltl.result import LTLResult
from aut2ltl.printer import format_result

_In = TypeVar("_In")

# On when FIRST_SUCCESS_TRACE or the global TRANSLATOR_TRACE_ON is set (presence).
# Built only inside `if _TRACE:`. Shows the choice ladder: each stage tried, whether
# it declined (and why) or won.
_TRACE = "FIRST_SUCCESS_TRACE" in os.environ or "TRANSLATOR_TRACE_ON" in os.environ


def _stage_name(stage: object) -> str:
    return getattr(stage, "name", type(stage).__name__)


class _FirstSuccess(Generic[_In]):
    """The chain-of-responsibility composite as a real, named translator: it
    obeys the Translator / CascadeTranslator interface (a fixed `name` plus a
    `__call__`), so a composite is itself a valid stage of another composite.

    Each stage is self-gating: a stage that does not apply to the input returns a
    DECLINED `LTLResult`, and the chain moves on. The winning stage's result —
    including its `technique` set — is returned unchanged (the composite stamps no
    tag of its own; its `name` is its identity, not a technique).
    """

    def __init__(
        self, name: str, stages: Sequence[Callable[[_In], LTLResult]]
    ) -> None:
        self.name = name
        self._stages = tuple(stages)

    def __call__(self, x: _In) -> LTLResult:
        # The single rule (see result.py): only DECLINED continues the chain. OK or a
        # NOT_LTL verdict both stop it — a verdict means no stage can produce a
        # faithful formula (a later stage would re-derive the same verdict), and
        # returning it preserves the reason. The terminal is a bare decline.
        for stage in self._stages:
            r = stage(x)
            if not r.declined:
                if _TRACE:
                    print(f"[first_success:{self.name}] {_stage_name(stage)} won -> "
                          + format_result(r), file=sys.stderr)
                return r
            if _TRACE:
                print(f"[first_success:{self.name}] {_stage_name(stage)} declined"
                      + (f": {r.diagnosis}" if r.diagnosis else ""), file=sys.stderr)
        if _TRACE:
            print(f"[first_success:{self.name}] all {len(self._stages)} stage(s) declined",
                  file=sys.stderr)
        return LTLResult.decline()


def first_success(
    stages: Sequence[Callable[[_In], LTLResult]],
    *,
    name: str,
) -> "_FirstSuccess[_In]":
    """Compose `stages` into a single named translator that returns the first
    stage whose result is OK (language-faithful), or a DECLINE if every stage
    declines. `name` is the composite's identity (passed at construction)."""
    return _FirstSuccess(name, stages)
