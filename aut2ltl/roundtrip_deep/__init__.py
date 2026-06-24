"""
aut2ltl.roundtrip_deep — the `deep_roundtrip` Rewriter (see algorithm.md).

`deep_roundtrip(R)` is a Rewriter (`LTLResult → LTLResult`): re-present every node of
the formula DAG bottom-up with `R`, memoized on node identity (one pass, DAG-complexity).
The whole-DAG, finder-free peer of `roundtrip` (one node) and `roundtrip_decomp` (a
node's operands) — the descent is the search.

Public entry: `deep_roundtrip`.
"""

from .deep_roundtrip import deep_roundtrip

__all__ = ["deep_roundtrip"]
