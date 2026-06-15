"""
aut2ltl/ltl/metrics.py — size metrics over a hash-consed `spot.formula` DAG.

The reconstruction returns a SHARED formula DAG (hash-consed end to end), so its
real complexity is the number of DISTINCT subformula nodes, not the size of the
flat string (which is the DAG unfolded — often orders of magnitude bigger). These
helpers quantify that gap for the front-end report and size surveys:

* `dag_node_count` — distinct nodes, a sharing-aware traversal keyed on `f.id()`.
* `tree_node_count` — the unfolded-tree node count, computed in O(DAG) by
  memoizing each shared node's subtree size (the VALUE can be astronomically
  large; computing it stays cheap). Optional `limit` saturates early.
* `dag_metrics` — both, plus the sharing factor, as one `DagMetrics`.

Engine-agnostic (a bare `spot.formula` in), so it lives in the shared `ltl` floor
below every engine — the front end and the size surveys both import it from here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import spot


# Temporal operators that mint a Spot acceptance set (the 32-set tableau driver);
# X is excluded — it does not create an acceptance condition.
_TEMPORAL_KINDS = frozenset({"U", "M", "R", "W", "F", "G"})


@dataclass(frozen=True)
class DagMetrics:
    """DAG vs unfolded-tree size of one formula (the sharing story), plus the
    count of distinct temporal nodes (the acceptance-set driver)."""

    dag_nodes: int
    tree_nodes: int
    temporal_nodes: int = 0

    @property
    def sharing(self) -> float:
        """tree/DAG — how many times the average shared node is reused."""
        return self.tree_nodes / self.dag_nodes if self.dag_nodes else 1.0


def dag_node_count(f: "spot.formula") -> int:
    """Distinct subformula nodes (hash-consed DAG size). Sharing-aware: each
    node id is visited once."""
    if f is None:
        return 0
    seen: set = set()
    stack = [f]
    while stack:
        g = stack.pop()
        gid = g.id()
        if gid in seen:
            continue
        seen.add(gid)
        for child in g:
            stack.append(child)
    return len(seen)


def tree_node_count(f: "spot.formula", limit: Optional[int] = None) -> int:
    """Unfolded-tree node count, memoized per shared node (so O(DAG), not
    O(tree)). With `limit` set, saturates at `limit` instead of computing the
    full (possibly astronomically large) value."""
    if f is None:
        return 0
    memo: Dict[int, int] = {}

    def rec(g: "spot.formula") -> int:
        gid = g.id()
        hit = memo.get(gid)
        if hit is not None:
            return hit
        total = 1
        for child in g:
            total += rec(child)
            if limit is not None and total >= limit:
                total = limit
                break
        memo[gid] = total
        return total

    return rec(f)


def temporal_node_count(f: "spot.formula") -> int:
    """Distinct temporal-operator nodes (kindstr in U/M/R/W/F/G — the Spot
    acceptance-set driver; X excluded). Sharing-aware: each node id once."""
    if f is None:
        return 0
    seen: set = set()
    temporal: set = set()
    stack = [f]
    while stack:
        g = stack.pop()
        gid = g.id()
        if gid in seen:
            continue
        seen.add(gid)
        if g.kindstr() in _TEMPORAL_KINDS:
            temporal.add(gid)
        for child in g:
            stack.append(child)
    return len(temporal)


def dag_metrics(f: "spot.formula") -> DagMetrics:
    """DAG node count + unfolded-tree node count + distinct-temporal count
    (+ sharing via the property)."""
    return DagMetrics(
        dag_nodes=dag_node_count(f),
        tree_nodes=tree_node_count(f),
        temporal_nodes=temporal_node_count(f),
    )


__all__ = [
    "DagMetrics", "dag_node_count", "tree_node_count",
    "temporal_node_count", "dag_metrics",
]
