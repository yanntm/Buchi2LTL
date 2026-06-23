#!/usr/bin/env python3
"""Probe: what does AccDecompose actually split GFa & FGb into?

Grounds the question "did acc2 pass the whole fragment, or split it?" by showing
the determinized form's acceptance + the per-conjunct pieces conjunct_pieces()
returns (count, acceptance, #states), then what daisy(core) labels each piece.
Single input, no argv. Run from project root.
"""
from typing import List

import spot

from aut2ltl.language import Language
from aut2ltl.options import Options
from aut2ltl.decomp.acceptance.acceptance import conjunct_pieces
from aut2ltl.portfolio.builder import daisy, core

F = "GFa & FGb"

lang = Language.of_ltl(F)
det = lang.det_generic_minimal()
print(f"formula            : {F}")
print(f"det_generic_minimal: {det.num_states()} states, acc = {det.get_acceptance()}")
print(f"top_conjuncts      : {list(det.acc().get_acceptance().top_conjuncts())}")

pieces: List["spot.twa_graph"] = conjunct_pieces(det)
print(f"\nconjunct_pieces -> {len(pieces)} piece(s)  "
      f"({'SPLIT' if pieces else 'NO SPLIT -> whole fragment to leaf'})")

leaf = daisy(core(Options()))
for i, p in enumerate(pieces):
    r = leaf(Language.of(p))
    print(f"  piece {i}: {p.num_states()} states, acc = {p.get_acceptance()}"
          f"  -> daisy/core = {r.formula}  [tech={r.technique}]")
