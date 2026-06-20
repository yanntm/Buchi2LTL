#!/usr/bin/env python3
"""
Smoke test for aut2ltl.ltl.metrics + aut2ltl.ltl.printers (GAP-free; bare
spot.formula DAGs in, no engine).

    python3 tests/test_ltl_metrics.py
"""
import sys

import spot

from aut2ltl.ltl.metrics import dag_node_count, tree_node_count, dag_metrics
from aut2ltl.ltl.printers import format_gated, to_dot

_fail = []

def check(cond: bool, msg: str) -> None:
    print(("ok  " if cond else "FAIL") + " : " + msg)
    if not cond:
        _fail.append(msg)

# A small formula with sharing: spot hash-conses `a`, `X a`, etc.
f = spot.formula("(X a) & (X a) | a")  # shared `X a`, shared `a`
dn = dag_node_count(f)
tn = tree_node_count(f)
check(dn >= 1 and tn >= dn, "tree_nodes >= dag_nodes >= 1")
m = dag_metrics(f)
check(m.dag_nodes == dn and m.tree_nodes == tn, "dag_metrics agrees with the counters")
check(m.sharing == tn / dn, "sharing factor = tree/dag")

# None is handled.
check(dag_node_count(None) == 0 and tree_node_count(None) == 0, "None counts as 0")
check(format_gated(None) == "false", "format_gated(None) == 'false'")

# Gated printing: above the limit -> placeholder; below -> the flat string.
big = spot.formula("a")
check(format_gated(big, limit=-1) == "a", "limit<0 always flattens")
check(format_gated(f, limit=1).startswith("<unflattened DAG:"),
      "tiny limit -> placeholder")
check(format_gated(f, limit=10_000) == str(f), "generous limit -> flat string")

# to_dot: pure-boolean subformula collapses to a single node; temporal sharing
# yields one node with multiple in-edges.
g = spot.formula("G(a | b) & X(a | b)")  # `a | b` is pure boolean (shared)
dot = to_dot(g)
check(dot.startswith("digraph formula {") and dot.rstrip().endswith("}"),
      "to_dot emits a digraph")
n_nodes = sum(1 for ln in dot.splitlines() if "[label=" in ln and "->" not in ln)
n_edges = dot.count("->")
# nodes: And, G, X, and one collapsed `a | b` leaf = 4; edges G->bool, X->bool,
# And->G, And->X = 4 (the boolean leaf is shared, one node, two in-edges).
check(n_nodes == 4, f"pure-boolean 'a|b' collapses to one node (got {n_nodes} nodes)")
check(n_edges == 4, f"4 edges incl. two into the shared boolean leaf (got {n_edges})")
check('label="a | b"' in dot or 'label="b | a"' in dot, "boolean leaf labelled by its spot string")
_bool_nodes = sum(1 for ln in to_dot(spot.formula("a & b")).splitlines()
                  if "[label=" in ln and "->" not in ln)
check(_bool_nodes == 1, "pure-boolean formula -> single node")
print("--- sample to_dot('G(a|b) & X(a|b)') ---")
print(dot)

print()
if _fail:
    print(f"FAILED {len(_fail)} check(s)")
    sys.exit(1)
print("ALL OK")
