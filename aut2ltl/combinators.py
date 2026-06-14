"""
aut2ltl/combinators.py — composite translators built over the contract.

A composite is itself a translator: it delegates to a collection of
sub-translators and combines their `LTLFormulaResult`s. Because every sub-result obeys
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

from typing import Callable, Generic, Sequence, TypeVar

from aut2ltl.contract import LTLFormulaResult

_In = TypeVar("_In")


class _FirstSuccess(Generic[_In]):
    """The chain-of-responsibility composite as a real, named translator: it
    obeys the Translator / CascadeTranslator interface (a fixed `name` plus a
    `__call__`), so a composite is itself a valid stage of another composite.

    Each stage is self-gating: a stage that does not apply to the input returns a
    DECLINED `LTLFormulaResult`, and the chain moves on. The winning stage's result —
    including its `technique` set — is returned unchanged (the composite stamps no
    tag of its own; its `name` is its identity, not a technique).
    """

    def __init__(
        self, name: str, stages: Sequence[Callable[[_In], LTLFormulaResult]]
    ) -> None:
        self.name = name
        self._stages = tuple(stages)

    def __call__(self, x: _In) -> LTLFormulaResult:
        for stage in self._stages:
            r = stage(x)
            if r.ok:
                return r
        return LTLFormulaResult.decline()


def first_success(
    stages: Sequence[Callable[[_In], LTLFormulaResult]],
    *,
    name: str,
) -> "_FirstSuccess[_In]":
    """Compose `stages` into a single named translator that returns the first
    stage whose result is OK (language-faithful), or a DECLINE if every stage
    declines. `name` is the composite's identity (passed at construction)."""
    return _FirstSuccess(name, stages)
