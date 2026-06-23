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

    Nodes are numbered by **memoized depth-first discovery order** (`n0` = root,
    then left-first descent, each shared node numbered once on first encounter),
    NOT by the per-process `spot.formula.id()`. Over a maximally hash-consed,
    child-ordered DAG that numbering is a function of structure alone, so the dot
    is **stable across processes/runs** — isomorphic DAGs serialize identically.
    (Spot interns identical subformulas and orders commutative operands, so the
    shared shape and child order are themselves canonical.)

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
    num: dict = {}  # spot id -> DFS-discovery index (transient id, never emitted)

    def label_of(g: "spot.formula", boolean: bool) -> str:
        s = str(g) if boolean else g.kindstr()
        if len(s) > max_label:
            s = s[: max_label - 3] + "..."
        return _dot_escape(s)

    def visit(g: "spot.formula") -> int:
        gid = g.id()
        if gid in num:
            return num[gid]
        n = len(num)
        num[gid] = n  # number on first visit, before descending (pre-order)
        boolean = g.is_boolean()
        fill = ", style=filled, fillcolor=lightgrey" if boolean else ""
        lines.append(f'  n{n} [label="{label_of(g, boolean)}"{fill}];')
        if boolean:
            return n  # collapse: a single node, do not expand the boolean tree
        children = list(g)
        multi = len(children) >= 2
        for i, c in enumerate(children):
            cn = visit(c)
            elabel = f' [label="{i}"]' if multi else ""
            lines.append(f"  n{n} -> n{cn}{elabel};")
        return n

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
