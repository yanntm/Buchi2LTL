"""
aut2ltl/best_of/best_of.py — the choice-by-size combinator.

`best_of` is the size-objective sibling of `first_success`: where `first_success`
takes the FIRST language-faithful stage (choice by cited order), `best_of` runs ALL
the stages and keeps the SMALLEST faithful result (choice by `cost`). Both obey the
same contract — every stage is language-faithful or DECLINED — so the winner is
sound by construction whichever one is chosen.
"""
from __future__ import annotations

from typing import Callable, Generic, Optional, Sequence, TypeVar

from aut2ltl.result import LTLResult

_In = TypeVar("_In")

# Comparable size key; `None` (no formula) sorts as +infinity so it never wins.
Key = Callable[[LTLResult], Optional[int]]


def _by_cost(r: LTLResult) -> Optional[int]:
    """Default key: the result's DAG-node count (`LTLResult.cost`)."""
    return r.cost


class _BestOf(Generic[_In]):
    """The choice-by-size composite as a real, named translator: it obeys the
    Translator / CascadeTranslator interface (a fixed `name` plus a `__call__`), so
    a composite is itself a valid stage of another composite.

    Each stage is self-gating (a stage that does not apply returns DECLINED). Unlike
    `first_success`, every applicable stage is run, and the OK result with the least
    `key` is returned UNCHANGED (the composite stamps no tag of its own; its `name`
    is its identity, not a technique). Ties keep the earlier stage (cited order is
    the tiebreak). A NOT_LTL from any stage short-circuits: the language is not
    LTL-definable, so no stage can produce a faithful formula and the verdict stands.
    """

    def __init__(
        self, name: str, stages: Sequence[Callable[[_In], LTLResult]], key: Key
    ) -> None:
        self.name = name
        self._stages = tuple(stages)
        self._key = key

    def __call__(self, x: _In) -> LTLResult:
        best: Optional[LTLResult] = None
        best_k: Optional[int] = None
        for stage in self._stages:
            r = stage(x)
            if r.not_ltl:
                return r                      # absorbing verdict: stop, keep reason
            if r.declined:
                continue                      # not this stage's case: move on
            k = self._key(r)                  # OK: a real candidate
            if best is None or (k is not None and (best_k is None or k < best_k)):
                best, best_k = r, k
        return best if best is not None else LTLResult.decline()


def best_of(
    stages: Sequence[Callable[[_In], LTLResult]],
    *,
    name: str,
    key: Key = _by_cost,
) -> "_BestOf[_In]":
    """Compose `stages` into a single named translator that runs every stage and
    returns the OK result minimizing `key` (default: DAG-node `cost`), a NOT_LTL
    verdict if any stage proves one, or a DECLINE if every stage declines. `name`
    is the composite's identity (passed at construction)."""
    return _BestOf(name, stages, key)
