"""
aut2ltl/translator.py — the contract floor: the `Translator` signature.

The single behavioral contract every engine and combinator implements. A Translator
is a callable `Language -> LTLResult`. This module is an interface: it states the
signature and the load-bearing invariant and depends on nothing — it names no
implementor (a contract exists without implementors).
"""
from __future__ import annotations

from typing import Protocol, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:
    from aut2ltl.language import Language
    from aut2ltl.result import LTLResult


@runtime_checkable
class Translator(Protocol):
    """The behavioral contract: translate a `Language` to LTL.

    A Translator is a callable `Language -> LTLResult`. The input is a `Language`
    (the floor handle over language-equivalent automaton representations —
    `aut2ltl.language`), not a raw automaton: each translator pulls the
    representation it wants (`tgba` / `det_parity_sbacc` / `det_generic` /
    `det_generic_minimal`).

    Contract invariant (NOT type-checkable, the load-bearing rule): the returned
    `LTLResult` is either language-faithful (`status` OK, `.formula` ≡ L(lang)) or a
    NOK (DECLINED / NOT_LTL) — NEVER a wrong formula. That single rule is what makes
    composition sound.
    """

    def __call__(self, lang: "Language") -> "LTLResult": ...


@runtime_checkable
class Decorator(Protocol):
    """The second sort of the combinator algebra: a `Translator -> Translator` map.

    A Decorator wraps a child translator into a new one — `StrengthDecompose`,
    `AccDecompose`, `Invariant`, `daisy_pair`, and a `recurse` step are all
    Decorators (each takes its recursion/floor target as its argument). Under
    composition (`∘`, `aut2ltl.combinators.compose.compose`) they form a monoid whose unit is
    `identity` — distinct from the `decline` *terminal* of the choice combinators
    (`first_success` / `best_of`); a terminal is an element, an identity is a map.

    Contract invariant (inherited, NOT type-checkable): a Decorator preserves the
    Translator faithful-or-NOK invariant — it returns a translator that is again
    language-faithful-or-declined — so any composition of Decorators stays sound by
    construction.
    """

    def __call__(self, child: "Translator") -> "Translator": ...
