"""
aut2ltl/bls/cascade_translator.py — the kr-internal cascade contract.

`CascadeTranslator` is the cascade-level peer of `Translator`, **private to the kr
engine**: it translates an already-decomposed Krohn-Rhodes cascade to LTL. It lives
in kr rather than the universal floor because only kr produces and consumes cascades.
"""
from __future__ import annotations

from typing import Protocol, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:
    from aut2ltl.result import LTLResult
    from aut2ltl.bls.cascade import CascadeHolder


@runtime_checkable
class CascadeTranslator(Protocol):
    """The cascade-level peer of `Translator`: translate a Krohn-Rhodes cascade to LTL.

    Same `LTLResult` and the same load-bearing invariant — the result is
    language-faithful (OK) or a NOK, never wrong — but the input is an already
    decomposed cascade (a `CascadeHolder` wrapping it) rather than a raw automaton.

    Realized as an OO family: each construction is a *member* — a small class
    (singleton instance) with a fixed `name` (its technique identity, e.g.
    'acc' / 'buchi' / 'cobuchi' / 'weak' / 'bls') and a `__call__` that is
    self-gating (it inspects the cascade and either builds its faithful form or
    DECLINES). The member stamps its own `name` into the `LTLResult`'s technique, so
    composites (`first_success`) need no out-of-band tagging. The holder wraps the
    pure `Cascade` with that build's caches/counters (bls/cascade/holder.py); members
    read cascade attributes off it transparently.
    """

    name: str

    def __call__(self, casc: "CascadeHolder") -> "LTLResult": ...
