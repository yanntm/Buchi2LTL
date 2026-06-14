"""
reachability.py — High-level LTL reconstruction from cascades using the paper K operators.

The core inductive operators (5 reachability formulas + fin_c) live in
reachability_operators.py.

This module provides the entry `reconstruct_bls` — the construction of
Boker, Lehtinen & Sickert, "On the Translation of Automata to Linear Temporal
Logic" (FoSSaCS 2022) — which delegates to the paper-faithful assembly
(reconstruct_ltl_paper_style): use of reach + fin_c (Lemma 7) + lifted Muller DNF
over good recurrent config sets (from Spot scc_info). No pattern matching,
no inf-often guessing, no special shortcuts for 1L/init-acc/trapping.
"""

from __future__ import annotations
import os
from typing import Any, Dict, List, Optional, Tuple

import spot

# Re-export the core operators so existing callers (examples, tests) continue to work.
# All 1L special case code has been deleted; the implementation is the pure generalized
# inductive 5 formulas for all depths.
from .reachability_operators import (  # noqa: F401
    letters_to_prop,
    make_guard,
    simplify_ltl,
    normalize_ltl,
    reach_strong,
    reach_weak,
    PAPER_REACH_CALLS,
    PAPER_FIN_CALLS,
    PAPER_MAX_LTL_SIZE,
)
from .fin import fin_c  # noqa: F401

from .cascade import Cascade

def reconstruct_ltl_paper_style(casc: Cascade, *, techniques=None) -> "spot.formula":
    """Acceptance-dispatch ladder over a cascade (§9.3 / Theorem 2).

    Tries the direct hierarchy-class leaves in order — acc → weak → buchi →
    cobuchi — each self-gating (it returns a faithful form or declines), and
    falls back to the general Muller-DNF core (`muller.reconstruct_muller`, the
    `bls` leaf) when none applies. Each leaf drops the explosive Fin web that the
    Muller form pays. Returns the hash-consed `spot.formula` DAG; serialization
    to text is a separate concern (`ltl_builders._str_f`), never done here.

    `techniques` (optional, default None): a SET the winning leaf's method tag is
    merged into (`acc`/`weak`/`buchi`/`cobuchi`/`bls`) for the portfolio report
    (`aut2ltl.contract.ReconResult`). None = no recording.

    Per-leaf gates: KR_DISPATCH_ACC / _WEAK / _BUCHI / _COBUCHI (=0 disables a
    leaf; weak is off by default).
    """
    def _tag(t):
        if techniques is not None:
            techniques.add(t)

    # Acc(c): the bounded / transient (X-ladder) fragment — self-gating, so safe
    # first in the chain and smallest for bounded inputs. Gate KR_DISPATCH_ACC.
    if os.environ.get("KR_DISPATCH_ACC", "1") != "0":
        from .acc import reconstruct_acc
        r = reconstruct_acc(casc)        # self-gating CascadeTranslator
        if r.ok:
            if techniques is not None:
                techniques |= r.technique
            return r.formula
    # Weak (Δ₁) / looping (Σ₁/Π₁): EXPERIMENTAL, OFF by default. Placed BEFORE
    # Büchi/coBüchi because weak languages are Büchi AND coBüchi recognizable —
    # those would otherwise claim them first — so weak only ever fires when its
    # gate is explicitly enabled. The cascade weak form is a size regression (the
    # residual is reach-driven); kept in, flagged off, for A/B against the coming
    # config-indexed Acc(c) weak-class construction. Gate KR_DISPATCH_WEAK.
    if os.environ.get("KR_DISPATCH_WEAK", "0") != "0":
        from .acceptance_dispatch import reconstruct_weak
        phi = reconstruct_weak(casc)
        if phi is not None:
            _tag("weak")
            return phi
    if os.environ.get("KR_DISPATCH_BUCHI", "1") != "0":
        from .acceptance_dispatch import reconstruct_buchi
        phi = reconstruct_buchi(casc)
        if phi is not None:
            _tag("buchi")
            return phi
    # coBüchi (persistence, Σ₂): tried AFTER Büchi, so it only sees
    # genuinely-not-Büchi cascades. φ = ⋀_{C∈α}Fin(C); gate recovers the natural
    # acceptance (the parity step hides coBüchi as Inf(0)|Fin(1)). Gate
    # KR_DISPATCH_COBUCHI, default ON.
    if os.environ.get("KR_DISPATCH_COBUCHI", "1") != "0":
        from .acceptance_dispatch import reconstruct_cobuchi
        phi = reconstruct_cobuchi(casc)
        if phi is not None:
            _tag("cobuchi")
            return phi
    # No simpler acceptance class applied: fall back to the general Muller-DNF
    # core (the `bls` leaf), which always produces a formula.
    _tag("bls")
    from .muller import reconstruct_muller
    return reconstruct_muller(casc)


def reconstruct_bls(casc: Cascade) -> "spot.formula":
    """Reconstruct LTL from a Cascade via the BLS construction.

    BLS = Boker, Lehtinen & Sickert, "On the Translation of Automata to Linear
    Temporal Logic" (FoSSaCS 2022) — the systematic algebraic translation from a
    counter-free deterministic ω-automaton to LTL over the Krohn-Rhodes / holonomy
    reset cascade. Delegates to the paper-faithful implementation: the five
    inductive reachability formulas (via fin_c for Lemma 7) + assembly of the
    Muller DNF over good recurrent config sets (reconstruct_ltl_paper_style).
    No ad-hoc, no shape inspection, no inf-often approximations. Returns the
    hash-consed spot.formula (see reconstruct_ltl_paper_style).
    """
    # Depth guard dropped (was 3 levels during find-issues-small-first dev):
    # the ladder is green through 3L and the construction is fully memoized
    # with a distinct-subproblem guard (KR_REACH_GUARD), which is the real
    # runaway protection. KR_MAX_LEVELS gives an opt-in ceiling if ever needed.
    max_levels = int(os.environ.get("KR_MAX_LEVELS", "0"))
    if max_levels > 0 and casc.num_levels > max_levels:
        raise NotImplementedError(
            f"Reconstruction depth ceiling KR_MAX_LEVELS={max_levels} "
            f"(got {casc.num_levels} levels)."
        )
    return reconstruct_ltl_paper_style(casc)


# --- Acceptance-type dispatch (TODO P1: construction-ref §9.3) ---

def build_phi(casc: Cascade, acceptance_type: str = "muller", acceptance_data=None) -> "spot.formula":
    """Acceptance-type dispatch. Muller — the primary, validated path —
    delegates to reconstruct_ltl_paper_style (formula object out).

    The direct hierarchy-preserving forms (looping-Büchi/coBüchi Σ₁/Π₁,
    Büchi/coBüchi Π₂/Σ₂, weak Δ₁ end_in(G)) are TODO P1; the previous
    string-pasting sketches for them were dropped with the str() API
    (they were placeholders with `if ...` ellipsis conditions, never live).
    """
    if acceptance_type in ("muller", None):
        return reconstruct_ltl_paper_style(casc)
    raise NotImplementedError(
        f"build_phi acceptance_type={acceptance_type!r}: direct "
        f"hierarchy-class forms are TODO P1 (construction-ref §9.3); "
        f"use the Muller path.")


__all__ = [
    "reconstruct_bls",
    "reconstruct_ltl_paper_style",
    "simplify_ltl",
    "normalize_ltl",
    "reach_strong",
    "reach_weak",
    "fin_c",
    "build_phi",
    # plus re-exports from operators (base cases + generalized)
]
