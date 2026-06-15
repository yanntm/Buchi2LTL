"""
kr — Krohn-Rhodes holonomy cascade support for systematic (paper-faithful) automaton to LTL.

The implementation follows the algebraic construction of Boker, Lehtinen & Sickert
(FoSSaCS 2022): deterministic complete parity automaton -> cascade decomp (SgpDec/GAP)
-> configuration automaton -> inductive 5 reachability formulas (K operators) + Fin(C)
(Lemma 7) + Muller DNF assembly for the lifted acceptance.

No ad-hoc pattern matching or approximations on automaton structure.

This package is the PURE cascade engine: no heuristics, no portfolio. The
decompose-and-recombine front end and the sl gate live in `aut2ltl.portfolio`;
the result struct lives in `aut2ltl.contract`.

See aut2ltl/kr/README.md, STATUS.md, algorithm.md .
"""

from .cascade import Cascade, CascadeHolder, LevelInfo, make_trivial_cascade
from .gap import (
    decompose_gens,
    decompose_aut,
    generate_gap_script,
    parse_cascade_output,
    run_gap_script,
    check_gap_available,
)
from .extract import extract_generators, ExtractionError, is_deterministic
from .reachability import (
    simplify_ltl,
    normalize_ltl,
    reach_strong,
    reach_weak,
    fin_c,
)
from .hierarchy_class import make_hierarchy_class, hierarchy_class
from .aut2cas import as_translator, reconstruct
from .reachability_operators import TRACE_ON  # for KR_TRACE=1 dev traces of inductive construction

__all__ = [
    "Cascade",
    "CascadeHolder",
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
    "make_hierarchy_class",
    "hierarchy_class",
    "as_translator",
    "reconstruct",
    "simplify_ltl",
    "normalize_ltl",
    "reach_strong",
    "reach_weak",
    "fin_c",
    "TRACE_ON",
]
