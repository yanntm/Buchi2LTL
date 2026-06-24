"""The `roundtrip_decomp` Rewriter (see algorithm.md).

`roundtrip_decomp(R, Φ)` locates `N = Φ(φ)`, re-presents each operand of `N` with the
Rewriter `R` (via `rewrite_each`), then rebuilds `N` from the rewritten operands and
substitutes it into `φ` once. When `N` is a `∧` / `∨` this is the intersection/union
decomposition; for any other node it is operand re-presentation. The operands are
rewritten as independent formulas and `N` is reassembled in a single edit, so no
hash-cons identity is invalidated in flight.
"""
from __future__ import annotations

from typing import Dict, List, TYPE_CHECKING

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

        operands: List["spot.formula"] = list(dict.fromkeys(node))   # distinct children, in order
        results = rewrite_each(operands, rewrite)

        out = LTLResult.start(name)
        out.credit(res)
        for r in results:
            out.credit(r)
            if out.nok:
                return out                               # a declined operand declines the whole

        mapping: Dict["spot.formula", "spot.formula"] = {
            op: r.formula for op, r in zip(operands, results)
        }
        rebuilt = node.map(lambda c: mapping[c])
        if rebuilt == node:
            return res                                   # nothing improved → no-op, no self-credit

        out.formula = substitute(formula, node, rebuilt)
        return out
    return run
