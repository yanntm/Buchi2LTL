"""
aut2ltl.sl — the heuristic LTL-reconstruction engine.

One of the two engines under the aut2ltl root (peer to `aut2ltl.kr`, the pure
cascade FoSSaCS construction). Its core, `sl` (self-loop / semi-linear backward
labeling), is an EXACT state-elimination translation on the very-weak (1-weak)
fragment and DECLINES (status DECLINED) elsewhere; the f2/t2 layer is a separate
verify-before-use guess-and-check. Sound by construction, so the portfolio gate
(`aut2ltl.portfolio.heuristic_gate`) can adopt its output without re-checking.

Imports only the contract floor (`aut2ltl.contract`); a peer of `aut2ltl.kr`,
importing neither it nor the portfolio. Public entry: `reconstruct_ltl(twa) ->
ReconResult`.
"""

from .reconstruction import reconstruct_ltl
from .heuristics.size2_overapprox import try_size2_overapprox
from .heuristics.terminal_2scc import try_terminal_2scc_with_validation
from .utils import simplify_ltl

__all__ = [
    "reconstruct_ltl",
    "try_size2_overapprox",
    "try_terminal_2scc_with_validation",
    "simplify_ltl",
]
