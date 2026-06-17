"""
kr.gap — the GAP/SgpDec bridge: automaton in, Krohn-Rhodes Cascade out.

Public entries: `decompose_aut(aut, ...) -> Cascade` (raw spot automaton) and
`decompose_lang(lang, ...) -> Cascade` (contract Language). See README.md in this
folder for the API, requirements, install, and module breakdown.
"""

from .bridge import decompose_gens, decompose_aut
from .decompose_lang import decompose_lang
from .export import generate_gap_script
from .runner import run_gap_script, check_gap_available
from .parse import parse_cascade_output

__all__ = [
    "decompose_gens",
    "decompose_aut",
    "decompose_lang",
    "generate_gap_script",
    "run_gap_script",
    "check_gap_available",
    "parse_cascade_output",
]
