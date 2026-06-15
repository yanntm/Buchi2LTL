"""
aut2ltl/ltl/printers.py — gated stringification of a formula DAG (output path).

Flattening a hash-consed `spot.formula` DAG to a string is O(unfolded tree): a
small DAG can unfold to a gigabyte. So the front end never calls `str()` blindly —
it flattens only when the unfolded tree is below a size gate, otherwise it prints a
placeholder naming the size. This is the OUTPUT-side peer of `aut2ltl.ltl.metrics`
(which counts) — here we render, using the metric to decide whether rendering is
affordable.

(`builders._str_f_gated` is the engine-internal version on the same gate; this
module is the public, exact, front-end renderer — it reuses `metrics.tree_node_count`
rather than the saturating internal walk.)
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .metrics import tree_node_count

if TYPE_CHECKING:
    import spot


def format_gated(f: Optional["spot.formula"], limit: Optional[int] = None) -> str:
    """Flatten `f` to a string, unless its unfolded tree exceeds `limit` nodes —
    then return `<unflattened DAG: N tree nodes>` instead of paying O(tree).
    `limit=None` or negative ⇒ always flatten. `f=None` ⇒ "false"."""
    if f is None:
        return "false"
    if limit is not None and limit >= 0:
        # Cheap O(DAG) gate probe (saturating one past the limit).
        if tree_node_count(f, limit=limit + 1) > limit:
            return f"<unflattened DAG: {tree_node_count(f)} tree nodes>"
    return str(f)


__all__ = ["format_gated"]
