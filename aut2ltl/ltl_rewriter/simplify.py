"""aut2ltl/ltl_rewriter/simplify.py — LTL simplification as a Rewriter.

Lifts `own_simplify` (aut2ltl/ltl) into the Rewriter contract: re-present a result's
formula by the DAG-size-aware own-rules pass. Faithful (own_simplify preserves the
language) and total (never declines). It credits a `simplify` tag **only when the
formula actually changed** — a no-op pass returns the input verbatim, uncredited.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from aut2ltl.result import LTLResult
from aut2ltl.ltl.builders import own_simplify

if TYPE_CHECKING:
    pass

_NAME = "simplify"


def simplify(res: "LTLResult") -> "LTLResult":
    """Rewriter: own-simplify the result's formula. Returns `res` verbatim when the
    pass is a no-op (same hash-consed handle), else a result credited `simplify`
    carrying the simplified formula and `res`'s provenance."""
    simplified = own_simplify(res.formula)
    if simplified == res.formula:        # hash-consed identity: nothing changed
        return res
    out = LTLResult.start(_NAME)
    out.credit(res)
    out.formula = simplified
    return out
