"""
aut2ltl.portfolio — the composition layer (combinators) over the engines.

A HOA is translated by whichever method wins at each node: the buchi2ltl/sl
gate, an AND/OR strength/acceptance split, or one of kr's leaf acceptance forms.
This package owns the cross-engine mixing (the runtime mutual recursion between
kr and sl); the engines themselves stay PEERS that import neither each other nor
this layer — only the contract floor (`aut2ltl.contract`).

Public entry: `reconstruct_decomposed(twa) -> ReconResult` (automaton in,
formula DAG + technique out). See aut2ltl/kr/TODO.md "THE MOVE CAMPAIGN".
"""

from .decompose_recombine import reconstruct_decomposed, split_report
from .heuristic_gate import try_heuristic_gate
from .sl_driven import reconstruct_sl_driven

__all__ = [
    "reconstruct_decomposed",
    "split_report",
    "try_heuristic_gate",
    "reconstruct_sl_driven",
]
