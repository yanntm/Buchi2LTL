"""
aut2ltl.ltl_rewriter — the `Rewriter` contract (`LTLResult → LTLResult`) and its
boundary adapters (see algorithm.md).

A Rewriter re-presents an already-held formula, faithful-or-declines, composing
through the existing `LTLResult` algebra. `identity` is the never-regress floor;
`simplify` lifts the LTL own-rules pass; `relabel` / `as_translator` are the two
adapters bridging the `Translator` world.

Public entries: `Rewriter`, `identity`, `simplify`, `relabel`, `as_translator`.
"""

from .rewriter import Rewriter, identity
from .simplify import simplify
from .adapt import relabel, as_translator

__all__ = ["Rewriter", "identity", "simplify", "relabel", "as_translator"]
