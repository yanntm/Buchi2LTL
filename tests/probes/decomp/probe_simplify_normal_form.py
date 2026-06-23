#!/usr/bin/env python3
"""Probe: is the GFa & FGb +1 a SIMPLIFIER normal-form choice, not a decomposition?

Takes the raw recombined conjunction `best` builds (FGb piece ∧ the daisy Inf piece)
and runs BOTH simplifiers — 'lo' (own DAG rules, what legacy runs per-recombine) and
'hi' (own + Spot, what best runs once at the end) — reporting tree size each way.
Also the clean conjunction without daisy's tautological conjunct. Single input.
"""
import spot

from aut2ltl.ltl.builders import own_simplify, _simp_f
from aut2ltl.ltl.metrics import dag_node_count, tree_node_count


def show(tag: str, raw: str) -> None:
    f = spot.formula(raw)
    lo = own_simplify(f)
    hi = _simp_f(f)
    print(f"{tag}")
    print(f"  raw : {f}")
    print(f"  lo  : {lo}   (dag {dag_node_count(lo)}, tree {tree_node_count(lo)})")
    print(f"  hi  : {hi}   (dag {dag_node_count(hi)}, tree {tree_node_count(hi)})")
    print()


# What daisy actually hands the And node (Inf piece carries the G(taut) conjunct):
show("daisy recombine (with tautological conjunct):",
     "(1 U (b & XGb)) & (G(!a | !b | (a & b)) & GF(a & b))")

# The clean conjunction (what sl_driven's per-piece forms recombine to):
show("clean recombine  FGb & GF(a & b):",
     "FGb & GF(a & b)")
