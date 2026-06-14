"""
kr.gap — the GAP/SgpDec bridge: automaton in, Krohn-Rhodes Cascade out.

Public entry: `decompose_aut(aut, ...) -> Cascade`. See README.md in this folder
for the API, requirements, install, and module breakdown.
"""

from .bridge import decompose_gens, decompose_aut
from .export import generate_gap_script
from .runner import run_gap_script, check_gap_available
from .parse import parse_cascade_output

__all__ = [
    "decompose_gens",
    "decompose_aut",
    "generate_gap_script",
    "run_gap_script",
    "check_gap_available",
    "parse_cascade_output",
]
