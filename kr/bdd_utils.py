"""
bdd_utils.py — Small helpers for reliable buddy BDD construction from Spot automata.

The original _valuation_to_bdd in extract.py did per-mask discovery of buddy var ids
by creating many tiny auts. This is fragile (var numbering can shift, interleaved
with & on the main aut's conditions can corrupt the bdd manager leading to sporadic
segfaults in the C extensions).

This module provides:
- get_ap_bdd_vars(aut) -> dict[int, int]   # ap_index -> buddy var id (computed once)
- build_point_bdd(aut, mask, aps, ap_vars=None) -> bdd   # concrete letter as bdd cube

Use the precomputed var map for all letters of one aut.
"""

from __future__ import annotations
from typing import Dict, List, Optional
import spot
import buddy


def get_ap_bdd_vars(aut: spot.twa_graph) -> Dict[int, int]:
    """Compute (once per aut) the mapping from AP index (in aut.ap()) to actual buddy variable id.

    Uses the same tiny-aut trick as before, but *only once*, upfront, before any
    point-bdd construction or & against the main aut's edge conditions.
    """
    aps = list(aut.ap())
    ap_to_var: Dict[int, int] = {}
    for i, ap in enumerate(aps):
        lit_f = spot.formula(str(ap))
        tmp = lit_f.translate()
        found = False
        for e in tmp.out(tmp.get_init_state_number()):
            cond = e.cond
            if cond != buddy.bddtrue and cond != buddy.bddfalse:
                ap_to_var[i] = buddy.bdd_var(cond)
                found = True
                break
        if not found:
            ap_to_var[i] = i  # fallback (rare)
    return ap_to_var


def build_point_bdd(
    aut: spot.twa_graph,
    mask: int,
    aps: List[spot.formula],
    ap_vars: Optional[Dict[int, int]] = None,
) -> "buddy.bdd":
    """Return a singleton (cube) BDD for the concrete valuation given by mask.

    If ap_vars (from get_ap_bdd_vars) is supplied, use it (strongly preferred).
    Otherwise falls back to on-the-fly discovery (old fragile behavior).
    """
    if ap_vars is None:
        ap_vars = get_ap_bdd_vars(aut)

    b = buddy.bddtrue
    for i, ap in enumerate(aps):
        v = ap_vars.get(i, i)
        bit = bool(mask & (1 << i))
        lit_bdd = buddy.bdd_ithvar(v) if bit else buddy.bdd_nithvar(v)
        b = b & lit_bdd
    return b
