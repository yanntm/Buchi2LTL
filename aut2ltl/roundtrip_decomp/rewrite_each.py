"""aut2ltl/roundtrip_decomp/rewrite_each.py — the per-node rewrite helper.

Apply a `Rewriter` to each of several independent nodes, one result per node. Each
node is rewritten as a standalone formula (wrapped `success(n)` only to meet the
Rewriter signature) — no shared carrier, so the rewrites are order-independent and
free of any hash-cons identity concern; reassembling them is the caller's job.
"""
from __future__ import annotations

from typing import List, Sequence, TYPE_CHECKING

from aut2ltl.result import LTLResult

if TYPE_CHECKING:
    import spot
    from aut2ltl.ltl_rewriter import Rewriter


def rewrite_each(nodes: Sequence["spot.formula"], rewrite: "Rewriter") -> List[LTLResult]:
    """Apply `rewrite` to each node independently — one `LTLResult` per node."""
    return [rewrite(LTLResult.success(n)) for n in nodes]
