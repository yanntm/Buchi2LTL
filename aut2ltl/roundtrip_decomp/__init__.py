"""
aut2ltl.roundtrip_decomp — the `roundtrip_decomp` Rewriter (see algorithm.md).

`roundtrip_decomp(R, Φ)` locates `N = Φ(φ)`, re-presents each operand of `N` with the
Rewriter `R`, rebuilds `N` and relinks once. The operand-decomposition peer of
`roundtrip`; `rewrite_each` is the per-node rewrite helper it folds over the operands.

Public entries: `roundtrip_decomp`, `rewrite_each`.
"""

from .rewrite_each import rewrite_each
from .roundtrip_decomp import roundtrip_decomp

__all__ = ["roundtrip_decomp", "rewrite_each"]
