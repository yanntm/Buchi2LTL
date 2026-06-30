"""
aut2ltl/ltl_rewriter/rewriter.py — the contract floor: the `Rewriter` signature.

A Rewriter is a callable `LTLResult -> LTLResult`: it re-presents an already-held
formula, keeping the `LTLResult` algebra (status, techniques, diagnosis) so rewriters
compose through the same monoids as translators. Like translator.py this module is an
interface — it states the signature and the load-bearing invariant and names no
implementor. The trivial `identity` rewriter (the never-regress floor) lives here.
"""
from __future__ import annotations

from typing import Protocol, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:
    from aut2ltl.result import LTLResult


@runtime_checkable
class Rewriter(Protocol):
    """The behavioral contract: re-present one LTL result as another.

    A Rewriter is a callable `LTLResult -> LTLResult`. The input is an OK result
    carrying a formula (and the provenance accumulated so far); the output is either
    language-faithful (status OK, `.formula` ≡ the input's) or a NOK (DECLINED) —
    NEVER a wrong formula. Decline closes composition (`first_of` / `best_of`);
    `identity` is the floor that never declines.

    Attribution rule (no-op ⇒ no credit). A Rewriter earns attribution only by an
    actual change to the formula. If it does not change the formula — its output is
    hash-cons-identical to the input (`out.formula == res.formula`) — it MUST return
    the input result VERBATIM, contributing no technique tag: neither its own, nor a
    delegate's. A finder that located a node, or a delegate that itself did nothing,
    is not work; only a changed formula is. So a composite Rewriter must short-circuit
    to its input whenever its rebuild reproduces it (`identity` and a no-op `simplify`
    already embody this), and must not pre-credit delegates it may end up discarding.
    """

    def __call__(self, res: "LTLResult") -> "LTLResult": ...


class Identity:
    """The unit Rewriter: returns its input result unchanged. Faithful, never
    declines. A named functor."""

    name = "identity"

    def __call__(self, res: "LTLResult") -> "LTLResult":
        return res


#: The singleton unit Rewriter.
identity: "Rewriter" = Identity()
