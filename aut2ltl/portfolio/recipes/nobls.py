"""nobls recipe — the full decomposition over `daisy_trio_det_inv`, floored on
`PartScc` ALONE (no bls cascade).

The `rich` arm of `cakedsdet`, but its floor is `PartScc()` instead of
`core = first(partscc, bls)` — so where a residual core is not a single terminal SCC
that `partscc` can label, the recipe **declines** rather than handing it to the bls
cascade. The motivation: the cascade leaves (notably `buchi`) emit blob formulas
(hundreds-to-thousands× the input on some U/R sub-languages — see
`tests/probes/roundtrip/probe_shared_nodes.py`). `nobls` refuses the cascade, so a
sub-language the decomposition/peel layers can't resolve is left for a round trip (or
a decline) rather than blown up. A probe of "no blowups if no buchi?".
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.partscc import PartScc
from aut2ltl.decomp.acceptance import AccDecompose
from aut2ltl.decomp.strength import StrengthDecompose
from aut2ltl.decomp.scc import SccDecompose
from aut2ltl.decomp.inv import Invariant
from aut2ltl.simplify_ltl import Simplify
from aut2ltl.compose import compose
from ..builder import daisy_trio_det_inv


def nobls(options: Optional[Options] = None) -> Translator:
    """`Invariant ∘ Strength ∘ Scc ∘ Invariant ∘ Acc ∘ daisy_trio_det_inv` over
    `PartScc()` (NO bls), wrapped in the `hi` simplifier. Declines where only the
    cascade could answer — never invokes a cascade leaf."""
    return Simplify(
        compose(Invariant, StrengthDecompose, SccDecompose,
                Invariant, AccDecompose, daisy_trio_det_inv)(PartScc()),
        "hi")


__all__ = ["nobls"]
