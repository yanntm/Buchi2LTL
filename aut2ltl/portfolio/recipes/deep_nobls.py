"""deep_nobls recipe — cakedsdet seed, then a DEEP (bottom-up) round trip via nobls.

Two labelers in the two already-separate slots: `cakedsdet` is the forward seed
(automaton → formula, the full assembly, blobs and all), and `nobls` is the return
labeler woven through a `deep_roundtrip` — re-presenting every node of the seed's DAG
bottom-up. `nobls` refuses the cascade, so a node it can re-derive comes back compact
(often smaller) and one it cannot is declined and kept; with the bottom-up order, a
shrunk child can drop its parent under the translate bound and the buchi tower
collapses from the leaves. Never-regress per node (`best_of([identity, relabel(nobls)])`),
a final `hi` simplifier over the whole.
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.combinators.best_of import best_of
from aut2ltl.ltl_rewriter import identity, relabel, as_translator
from aut2ltl.roundtrip_deep import deep_roundtrip
from aut2ltl.simplify_ltl import Simplify
from .cakedsdet import cakedsdet
from .nobls import nobls


def deep_nobls(options: Optional[Options] = None) -> Translator:
    """`cakedsdet` seeds a formula; `deep_roundtrip` then re-presents every DAG node
    bottom-up via `nobls`, kept per node only when not larger
    (`best_of([identity, relabel(nobls)])`); a final `hi` simplifier over the whole."""
    represent = best_of([identity, relabel(nobls(options))], name="deep_nobls_arm")
    rewriter = deep_roundtrip(represent)
    return Simplify(as_translator(cakedsdet(options), rewriter), "hi")


__all__ = ["deep_nobls"]
