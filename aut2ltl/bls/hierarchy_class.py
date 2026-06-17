"""
kr/hierarchy_class.py — the hierarchy-class CascadeTranslator.

Acceptance-dispatch ladder over a cascade (§9.3 / Theorem 2), as a configured
`first_success` chain over the acceptance-class members. Tries the direct
hierarchy-class leaves in order — acc → weak → buchi → cobuchi — each self-gating
(it returns a faithful form or declines), and falls back to the general-case
`bls` member (the full Muller-DNF construction) when none applies. Each leaf
drops the explosive Fin web that the Muller form pays. The chain forwards the
winning leaf's `LTLResult` unchanged, so `.technique` reports the winning
leaf's method tag (`acc`/`weak`/`buchi`/`cobuchi`/`bls`); the formula it carries
is the hash-consed `spot.formula` DAG (serialization to text is a separate
concern — `ltl_builders._str_f` — never done here).

Per-leaf gates are the `kr.dispatch.*` Options (declared in `kr/options.py`,
seeded from the legacy KR_DISPATCH_* env vars): each =False drops a leaf; weak is
off by default. The chain membership is read once, HERE, at construction — passing
a different `Options` builds a different chain (the A/B move). The build-state
counters are a separate (Caches) pass. The module builds one default singleton,
`hierarchy_class`, from the env-seeded default Options.
"""

from __future__ import annotations

from typing import List, Optional

from .cascade_translator import CascadeTranslator
from aut2ltl.first_success import first_success
from aut2ltl.options import Options
from .options import (
    KR_DISPATCH_OPTIONS, DISPATCH_ACC, DISPATCH_WEAK, DISPATCH_BUCHI, DISPATCH_COBUCHI,
)
from .acc import acc as _acc
from .buchi import buchi as _buchi
from .cobuchi import cobuchi as _cobuchi
from .weak import weak as _weak
from .bls import bls as _bls


def make_hierarchy_class(options: Optional[Options] = None) -> CascadeTranslator:
    """Build the hierarchy-class chain: a named `first_success` over the
    acceptance-class leaves in order acc → weak → buchi → cobuchi → bls, honoring
    the per-leaf `kr.dispatch.*` Options. `bls` is always last and never declines.
    `options=None` ⇒ the env-seeded default (legacy KR_DISPATCH_* behaviour)."""
    if options is None:
        options = Options.from_specs(KR_DISPATCH_OPTIONS)
    members: List[CascadeTranslator] = []
    # Acc(c): the bounded / transient (X-ladder) fragment — self-gating, so safe
    # first in the chain and smallest for bounded inputs. Gate kr.dispatch.acc.
    if options.get(DISPATCH_ACC):
        members.append(_acc)
    # Weak (Δ₁): off by default (kr.dispatch.weak). Placed before Büchi/coBüchi —
    # weak languages are Büchi AND coBüchi recognizable, so they would otherwise
    # claim weak cases first; this only fires when its gate is enabled.
    if options.get(DISPATCH_WEAK):
        members.append(_weak)
    if options.get(DISPATCH_BUCHI):
        members.append(_buchi)
    # coBüchi (persistence, Σ₂): tried after Büchi, so it only sees
    # genuinely-not-Büchi cascades. Gate kr.dispatch.cobuchi, default ON.
    if options.get(DISPATCH_COBUCHI):
        members.append(_cobuchi)
    # No simpler acceptance class applied: fall back to the general-case `bls`
    # member (the full Muller-DNF construction), which always produces a formula.
    members.append(_bls)
    return first_success(members, name="hierarchy_class")


hierarchy_class: CascadeTranslator = make_hierarchy_class()


__all__ = ["make_hierarchy_class", "hierarchy_class"]
