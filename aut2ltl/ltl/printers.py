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

from typing import List, Optional, TYPE_CHECKING

from .metrics import tree_node_count

if TYPE_CHECKING:
    import spot


def _dot_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def to_dot(f: Optional["spot.formula"], max_label: int = 60) -> str:
    """Graphviz dot of the hash-consed formula DAG — O(distinct nodes), never the
    unfolded O(tree), so it does not explode where the flat string would.

    Sharing is visible directly: a subformula reused N times is ONE node with N
    in-edges (the structure the flat string hides). PURE-BOOLEAN subformulas
    (`f.is_boolean()` — no temporal operator inside) are collapsed into a single
    leaf node labelled with their flat string instead of expanding their boolean
    tree, so the graph shows only the temporal skeleton and stays bounded by the
    boolean width too (labels truncated to `max_label`). Temporal nodes are
    labelled by their operator (`kindstr`); edges of an n-ary/binary operator are
    indexed so the non-commutative ones (U/R/W/M) stay readable."""
    if f is None:
        return "digraph formula {\n  n0 [label=\"false\"];\n}\n"
    lines: List[str] = [
        "digraph formula {",
        '  node [shape=box, fontname="monospace"];',
    ]
    seen: set = set()

    def label_of(g: "spot.formula", boolean: bool) -> str:
        s = str(g) if boolean else g.kindstr()
        if len(s) > max_label:
            s = s[: max_label - 3] + "..."
        return _dot_escape(s)

    def visit(g: "spot.formula") -> None:
        gid = g.id()
        if gid in seen:
            return
        seen.add(gid)
        boolean = g.is_boolean()
        fill = ", style=filled, fillcolor=lightgrey" if boolean else ""
        lines.append(f'  n{gid} [label="{label_of(g, boolean)}"{fill}];')
        if boolean:
            return  # collapse: a single node, do not expand the boolean tree
        children = list(g)
        multi = len(children) >= 2
        for i, c in enumerate(children):
            visit(c)
            elabel = f' [label="{i}"]' if multi else ""
            lines.append(f"  n{gid} -> n{c.id()}{elabel};")

    visit(f)
    lines.append("}")
    return "\n".join(lines) + "\n"


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
