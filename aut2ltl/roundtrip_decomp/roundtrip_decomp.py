"""The `roundtrip_decomp` Rewriter (see algorithm.md).

`roundtrip_decomp(R, Φ)` locates `N = Φ(φ)`, re-presents each operand of `N` with the
Rewriter `R` (via `rewrite_each`), then rebuilds `N` from the rewritten operands and
substitutes it into `φ` once. When `N` is a `∧` / `∨` this is the intersection/union
decomposition; for any other node it is operand re-presentation. The operands are
rewritten as independent formulas and `N` is reassembled in a single edit, so no
hash-cons identity is invalidated in flight.
"""
from __future__ import annotations

from typing import List, TYPE_CHECKING

from aut2ltl.result import LTLResult
from aut2ltl.roundtrip.subst import substitute
from .rewrite_each import rewrite_each

if TYPE_CHECKING:
    import spot
    from aut2ltl.ltl_rewriter import Rewriter
    from aut2ltl.roundtrip.finder import Finder

_NAME = "roundtrip_decomp"


def roundtrip_decomp(rewrite: "Rewriter", finder: "Finder", *, name: str = _NAME) -> "Rewriter":
    """Build a Rewriter re-presenting the operands of one located node. Locate
    `N = finder(res.formula)`; re-present each distinct operand with `rewrite`;
    rebuild `N` from the results and substitute it into the formula once. A declined
    finder, or a no-op (no operand improved), returns the input verbatim
    (uncredited); a declined operand re-presentation declines the whole."""
    def run(res: LTLResult) -> LTLResult:
        formula = res.formula
        node = finder(formula)
        if node is None:
            return res                                   # finder declines → identity

        operands: List["spot.formula"] = list(node)   # children, in order (duplicates kept)
        results = rewrite_each(operands, rewrite)

        out = LTLResult.start(name)
        out.credit(res)
        for r in results:
            out.credit(r)
            if out.nok:
                return out                               # a declined operand declines the whole

        # Rebuild N from the re-presented operands, fed back in order. We must NOT
        # look the children up by value: rewriting an operand can drift the child
        # instance held inside `node` out from under a value-keyed map (spot
        # re-presents shared sub-structure in place). `operands` was snapshotted
        # from `node` in order and `results` is parallel to it, so a positional
        # feed — ignoring the live child `node.map` hands us — is identity-safe.
        rebuilt_operands = iter(r.formula for r in results)
        rebuilt = node.map(lambda _c: next(rebuilt_operands))
        if rebuilt == node:
            return res                                   # nothing improved → no-op, no self-credit

        out.formula = substitute(formula, node, rebuilt)
        return out
    return run
