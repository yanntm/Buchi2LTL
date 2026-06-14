"""
aut2ltl.portfolio — the composition layer (combinators) over the engines.

A `Language` is translated by whichever Translator wins at each node: the sl gate,
an AND/OR strength/acceptance split (`Decompose`), the sl-driven blaster, or the
kr cascade. Every piece is a Translator (`Language -> LTLFormulaResult`); the
engines stay PEERS importing only the contract floor (`aut2ltl.contract` /
`aut2ltl.language`).

The default entry `reconstruct_decomposed` is the assembled composition:

    cascade   = aut2cas.reconstruct                        # the kr cascade Translator
    core      = Decompose(first_success([sl, cascade]))    # SlDriven's non-recursing delegate
    sl_driven = SlDriven(delegate=core)                    # the blaster ("kr under sl")
    reconstruct_decomposed = Decompose(first_success([sl_driven, cascade]))

`reconstruct_decomposed` splits the input, then hands each atom to the blaster
(sl envelope + delegated cores), with the cascade as the always-succeeds floor.
`core` does NOT contain `SlDriven`, so the kr↔sl recursion shrinks to the cascade
and terminates.
"""
from __future__ import annotations

from aut2ltl.combinators import first_success
from aut2ltl.options import Options
from aut2ltl.kr.options import KR_OPTIONS
from aut2ltl.kr.aut2cas import as_translator
from aut2ltl.kr.hierarchy_class import make_hierarchy_class
from .options import PORTFOLIO_OPTIONS
from .sl import Sl
from .sl_driven import SlDriven
from .decompose import Decompose, split_report

# One shared default Options threaded through the whole graph: the object graph IS
# the config graph. Seeded from the full contract (portfolio + kr) so the legacy
# env bridge covers every declared knob, even those not yet read via options.get.
# A caller wanting a variant rebuilds the graph with `make_*`/constructors and a
# cloned Options (the A/B move); these module singletons are the env-seeded default.
_options = Options.from_specs(PORTFOLIO_OPTIONS + KR_OPTIONS)

# The assembled default portfolio Translators (all Language -> LTLFormulaResult).
sl = Sl(_options)                                          # the sl gate
cascade = as_translator(make_hierarchy_class(_options))    # the kr cascade Translator
core = Decompose(first_success([sl, cascade], name="core"))
sl_driven = SlDriven(delegate=core)
reconstruct_decomposed = Decompose(first_success([sl_driven, cascade], name="top"))

__all__ = [
    "reconstruct_decomposed",
    "split_report",
    "Sl",
    "sl",
    "SlDriven",
    "sl_driven",
    "Decompose",
    "cascade",
    "core",
    "first_success",
]
