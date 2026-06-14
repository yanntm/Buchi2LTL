"""
kr — Krohn-Rhodes holonomy cascade support for systematic (paper-faithful) automaton to LTL.

The implementation follows the algebraic construction of Boker, Lehtinen & Sickert
(FoSSaCS 2022): deterministic complete parity automaton -> cascade decomp (SgpDec/GAP)
-> configuration automaton -> inductive 5 reachability formulas (K operators) + Fin(C)
(Lemma 7) + Muller DNF assembly for the lifted acceptance.

No ad-hoc pattern matching or approximations on automaton structure.

See kr/README.md, kr/STATUS.md, kr/algorithm.md .
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
    reconstruct_bls,
    reconstruct_ltl_paper_style,
    reconstruct_ltl_str,
    simplify_ltl,
    normalize_ltl,
    reach_strong,
    reach_weak,
    fin_c,
)
from .reachability_operators import TRACE_ON  # for KR_TRACE=1 dev traces of inductive construction
from .decompose_recombine import reconstruct_decomposed, split_report
from .recon_result import ReconResult

__all__ = [
    "ReconResult",
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
    "reconstruct_decomposed",
    "split_report",
    "reconstruct_bls",
    "reconstruct_ltl_paper_style",
    "reconstruct_ltl_str",
    "simplify_ltl",
    "normalize_ltl",
    "reach_strong",
    "reach_weak",
    "fin_c",
    "TRACE_ON",
]
