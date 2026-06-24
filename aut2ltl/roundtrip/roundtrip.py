"""The `roundtrip` Rewriter (see algorithm.md).

`roundtrip(R, Φ)` locates one node of the input formula via the finder `Φ`,
re-presents the subformula there with the Rewriter `R`, and relinks the result in
place. No seed — seeding is `as_translator`'s concern (see `ltl_rewriter`). With
`R = relabel(Λ)` the re-presentation is the language round trip; with `R` tied to a
decomposer the re-derivation recurses.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from aut2ltl.result import LTLResult
from .subst import substitute

if TYPE_CHECKING:
    from aut2ltl.ltl_rewriter import Rewriter
    from .finder import Finder

_NAME = "roundtrip"


def roundtrip(rewrite: Rewriter, finder: Finder, *, name: str = _NAME) -> Rewriter:
    """Build a Rewriter re-presenting one located node: `n = finder(res.formula)`,
    re-present `res.formula↓n` (= `n`) with `rewrite`, relink. A declined finder
    returns the input verbatim (no self-credit); a declined re-presentation
    propagates (unmasked)."""
    def run(res: LTLResult) -> LTLResult:
        formula = res.formula
        node = finder(formula)
        if node is None:
            return res                              # finder declines → identity
        inner = rewrite(LTLResult.success(node))    # re-present the located node
        if inner.nok:
            return inner                            # decline propagates; not masked
        out = LTLResult.start(name)
        out.credit(res)
        out.credit(inner)
        out.formula = substitute(formula, node, inner.formula)
        return out
    return run
