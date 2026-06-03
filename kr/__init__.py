"""
kr — Experimental Krohn-Rhodes (holonomy cascade) support for Buchi → LTL.

Public API (first milestone):
    from kr import Cascade, decompose_gens, decompose_aut, generate_gap_script
    from kr.extract import extract_generators
    from kr.cascade import LevelInfo

See kr/README.md and the top-level project README for context and status.
"""

from .cascade import Cascade, LevelInfo, make_trivial_cascade
from .gap_bridge import (
    decompose_gens,
    decompose_aut,
    generate_gap_script,
    parse_cascade_output,
    run_gap_script,
    check_gap_available,
)
from .extract import extract_generators, ExtractionError, is_deterministic
from .reachability import (
    one_level_reach_stay,
    one_level_reach_strong,
    build_1level_reachability,
    fin_1level,
    inf_1level,
    reconstruct_ltl_1level_buchi,
    reconstruct_ltl_1level_buchi_heuristic,
    build_infinitely_often_accepting,
    simplify_ltl,
    normalize_ltl,
    reach_strong,
    reach_weak,
    fin_c,
)

__all__ = [
    "Cascade",
    "LevelInfo",
    "make_trivial_cascade",
    "decompose_gens",
    "decompose_aut",
    "generate_gap_script",
    "parse_cascade_output",
    "run_gap_script",
    "check_gap_available",
    "extract_generators",
    "ExtractionError",
    "is_deterministic",
    "one_level_reach_stay",
    "one_level_reach_strong",
    "build_1level_reachability",
    "fin_1level",
    "inf_1level",
    "reconstruct_ltl_1level_buchi",
    "reconstruct_ltl_1level_buchi_heuristic",
    "build_infinitely_often_accepting",
    "simplify_ltl",
    "normalize_ltl",
    "reach_strong",
    "reach_weak",
    "fin_c",
]
