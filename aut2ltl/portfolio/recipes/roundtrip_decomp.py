"""roundtrip_decomp recipe — split the top-level AND, re-present each conjunct.

Delegate to `cakedsdet` (what `RECIPES["default"]` points at — our current best) as
both seed and per-conjunct labeler: seed a formula, locate its top-level `∧`, and
re-present each conjunct's language independently with `cakedsdet` — keeping the
conjunct as-is unless the re-derivation is strictly smaller — rebuild the `∧`, then
run a final `hi` simplification over the whole.
"""
from __future__ import annotations

from typing import Optional

import spot

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.combinators.best_of import best_of
from aut2ltl.ltl_rewriter import identity, relabel, as_translator
from aut2ltl.roundtrip_decomp import roundtrip_decomp
from aut2ltl.roundtrip.cutpoints import toplevel
from aut2ltl.simplify_ltl import Simplify
from .cakedsdet import cakedsdet


def roundtrip_decomp_recipe(options: Optional[Options] = None) -> Translator:
    """`cakedsdet` seeding a formula, its top-level `∧` decomposed: each conjunct's
    language re-presented with `cakedsdet`, kept only when smaller than the conjunct
    (`best_of(identity, relabel)`), the `∧` rebuilt, and a final `hi` simplifier over
    the rebuilt whole."""
    child = cakedsdet(options)
    per_conjunct = best_of([identity, relabel(child)], name="roundtrip_decomp_arm")
    rewriter = roundtrip_decomp(per_conjunct, toplevel(spot.op_And))
    return Simplify(as_translator(child, rewriter), "hi")


__all__ = ["roundtrip_decomp_recipe"]
