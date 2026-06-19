"""roundtrip recipe — the current best (`cakedsdet`, the default) behind a round trip.

A first round-trip variant, top-level: delegate to `cakedsdet` (what
`RECIPES["default"]` points at — our current best), wrap it in a single `Roundtrip`
so its formula is re-derived through one Language round trip, and run a final `hi`
simplification pass over the whole.
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.roundtrip import Roundtrip
from aut2ltl.simplify_ltl import Simplify
from .cakedsdet import cakedsdet


def roundtrip(options: Optional[Options] = None) -> Translator:
    """`cakedsdet` (the current default/best) wrapped in one `Roundtrip` under a final
    `hi` simplifier: seed a formula with `cakedsdet`, re-describe the language by it,
    relabel with `cakedsdet` on the fresh presentation, then simplify the result."""
    return Simplify(Roundtrip(cakedsdet(options)), "hi")


__all__ = ["roundtrip"]
