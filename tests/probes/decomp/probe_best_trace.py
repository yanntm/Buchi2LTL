#!/usr/bin/env python3
"""Trace the actual `best` assembly on GFa & FGb, stage by stage, to see where the
8-node form comes from despite the per-daisy lo simplify."""
import spot

from aut2ltl.language import Language
from aut2ltl.options import Options
from aut2ltl.decomp.acceptance import AccDecompose
from aut2ltl.decomp.strength import StrengthDecompose
from aut2ltl.simplify_ltl import Simplify
from aut2ltl.portfolio.builder import daisy, core
from aut2ltl.ltl.metrics import dag_node_count as dag

F = "GFa & FGb"
opts = Options()
leaf = Simplify(daisy(core(opts)), "lo")

acc = AccDecompose(leaf)
r_acc = acc(Language.of_ltl(F))
print(f"AccDecompose(leaf)          -> {r_acc.formula}  (dag {dag(r_acc.formula)})  tech={sorted(r_acc.technique)}")

strg = StrengthDecompose(acc)
r_strg = strg(Language.of_ltl(F))
print(f"StrengthDecompose(Acc(leaf))-> {r_strg.formula}  (dag {dag(r_strg.formula)})  tech={sorted(r_strg.technique)}")

whole = Simplify(strg, "hi")
r = whole(Language.of_ltl(F))
print(f"Simplify(...,'hi') = best    -> {r.formula}  (dag {dag(r.formula)})  tech={sorted(r.technique)}")
