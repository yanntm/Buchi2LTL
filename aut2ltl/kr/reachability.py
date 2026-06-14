"""
reachability.py — re-export hub for the paper K operators.

The core inductive operators (the 5 reachability formulas + fin_c) live in
reachability_operators.py and fin.py. LTL reconstruction from a cascade is now the
CascadeTranslator members (kr/{acc,buchi,cobuchi,weak,bls}.py) composed by
kr/hierarchy_class.py, lifted to the automaton level by kr/aut2cas.py. This module
only re-exports the operators so existing callers (examples, tests) continue to
work.
"""

from __future__ import annotations

# Re-export the core operators so existing callers (examples, tests) continue to work.
# All 1L special case code has been deleted; the implementation is the pure generalized
# inductive 5 formulas for all depths.
from .reachability_operators import (  # noqa: F401
    letters_to_prop,
    make_guard,
    simplify_ltl,
    normalize_ltl,
    reach_strong,
    reach_weak,
    PAPER_REACH_CALLS,
    PAPER_FIN_CALLS,
    PAPER_MAX_LTL_SIZE,
)
from .fin import fin_c  # noqa: F401

__all__ = [
    "simplify_ltl",
    "normalize_ltl",
    "reach_strong",
    "reach_weak",
    "fin_c",
    # plus re-exports from operators (base cases + generalized)
]
