"""
kr/hierarchy_class.py — the hierarchy-class CascadeTranslator.

Acceptance-dispatch ladder over a cascade (§9.3 / Theorem 2), as a configured
`first_success` chain over the acceptance-class members. Tries the direct
hierarchy-class leaves in order — acc → weak → buchi → cobuchi — each self-gating
(it returns a faithful form or declines), and falls back to the general-case
`bls` member (the full Muller-DNF construction) when none applies. Each leaf
drops the explosive Fin web that the Muller form pays. The chain forwards the
winning leaf's `LTLFormulaResult` unchanged, so `.technique` reports the winning
leaf's method tag (`acc`/`weak`/`buchi`/`cobuchi`/`bls`); the formula it carries
is the hash-consed `spot.formula` DAG (serialization to text is a separate
concern — `ltl_builders._str_f` — never done here).

Per-leaf gates: KR_DISPATCH_ACC / _WEAK / _BUCHI / _COBUCHI (=0 disables a leaf;
weak is off by default). The cleanup of these env knobs (and the build-state
counters) is a separate pass; left as-is for now. The module builds one default
singleton, `hierarchy_class`.
"""

from __future__ import annotations

import os
from typing import List

from aut2ltl.contract import CascadeTranslator
from aut2ltl.combinators import first_success
from .acc import acc as _acc
from .buchi import buchi as _buchi
from .cobuchi import cobuchi as _cobuchi
from .weak import weak as _weak
from .bls import bls as _bls


def make_hierarchy_class() -> CascadeTranslator:
    """Build the hierarchy-class chain: a named `first_success` over the
    acceptance-class leaves in order acc → weak → buchi → cobuchi → bls, honoring
    the per-leaf KR_DISPATCH_* gates. `bls` is always last and never declines."""
    members: List[CascadeTranslator] = []
    # Acc(c): the bounded / transient (X-ladder) fragment — self-gating, so safe
    # first in the chain and smallest for bounded inputs. Gate KR_DISPATCH_ACC.
    if os.environ.get("KR_DISPATCH_ACC", "1") != "0":
        members.append(_acc)
    # Weak (Δ₁): off by default (KR_DISPATCH_WEAK). Placed before Büchi/coBüchi —
    # weak languages are Büchi AND coBüchi recognizable, so they would otherwise
    # claim weak cases first; this only fires when its gate is enabled.
    if os.environ.get("KR_DISPATCH_WEAK", "0") != "0":
        members.append(_weak)
    if os.environ.get("KR_DISPATCH_BUCHI", "1") != "0":
        members.append(_buchi)
    # coBüchi (persistence, Σ₂): tried after Büchi, so it only sees
    # genuinely-not-Büchi cascades. Gate KR_DISPATCH_COBUCHI, default ON.
    if os.environ.get("KR_DISPATCH_COBUCHI", "1") != "0":
        members.append(_cobuchi)
    # No simpler acceptance class applied: fall back to the general-case `bls`
    # member (the full Muller-DNF construction), which always produces a formula.
    members.append(_bls)
    return first_success(members, name="hierarchy_class")


hierarchy_class: CascadeTranslator = make_hierarchy_class()


__all__ = ["make_hierarchy_class", "hierarchy_class"]
