"""
kr/sl_driven.py — sl-driven reconstruction with kr delegation ("kr UNDER sl").

The mirror of the decompose gate (which is "sl under kr"). Here sl is the
DRIVER: `reconstruct_sl_driven(aut)` runs buchi2ltl's exact self-loop backward
labeling, and wherever sl reaches a state it cannot translate (a multi-state
SCC), it delegates the whole sub-automaton from that state to the NORMAL kr
pipeline `reconstruct_decomposed` (decompose + the sl gate + the cascade) and
reattaches the returned label. sl handles the very-weak envelope exactly and
tiny; kr handles the multi-cyclic core — on a SMALLER automaton than the whole
(kr's cost tracks state count, so peeling a prefix is the structural win).

Soundness: the delegated label is L(sub) = exactly the language sl's own
label(q) would represent, so substituting a sound translator's label is
interchangeable with sl's; the surrounding sl construction (already validated)
composes it correctly (X-wrapped at the crossing edge, invariants re-added).

Termination / no ping-pong: the delegated `reconstruct_decomposed` uses the sl
GATE (`try_heuristic_gate`, with NO scc_labeler), which DECLINES the multi-state
core and routes it to the kr cascade. Delegation therefore bottoms out in the
cascade, never back in the sl-driver.

Orthogonal: nothing in kr imports this; the only buchi2ltl change is the
optional `scc_labeler` param (default None = unchanged behavior).
"""
from __future__ import annotations

from typing import Optional

import spot

from .decompose_recombine import reconstruct_decomposed

__all__ = ["reconstruct_sl_driven"]


def reconstruct_sl_driven(aut: "spot.twa_graph") -> Optional["spot.formula"]:
    """sl-driven reconstruction with kr delegation. Returns a hash-consed
    formula DAG, or None if sl declines AND every delegation also declined
    (i.e. the whole thing is unreconstructable by this composition)."""
    from buchi2ltl.reconstruction import reconstruct_ltl

    def labeler(sub: "spot.twa_graph") -> Optional["spot.formula"]:
        # Return the kr DAG DIRECTLY (no str()): the DAG-native engine splices it
        # as a child node WITHOUT flattening — the whole point of the rewrite.
        # A high-sharing core that would explode str() now costs only its DAG.
        try:
            return reconstruct_decomposed(sub).formula
        except Exception:
            return None

    tgba = spot.postprocess(aut, "TGBA", "Small", "High")
    try:
        out = reconstruct_ltl(tgba, scc_labeler=labeler)
    except Exception:
        return None
    if out.declined or out.formula is None:   # ReconResult: "not me"
        return None
    rec = out.formula
    try:
        cand = rec if isinstance(rec, spot.formula) else spot.formula(str(rec))
    except Exception:
        return None
    # Simplify on equal footing with the rest of the pipeline (buchi2ltl skips
    # Spot's simplifier; the spliced kr labels are already simplified).
    try:
        from .ltl_builders import _simp_f
        cand = _simp_f(cand)
    except Exception:
        pass
    return cand
