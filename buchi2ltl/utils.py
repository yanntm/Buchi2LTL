"""
Small utilities for the BuchiToLTL prototype.
"""

import spot


def simplify_ltl(formula_str: str) -> str:
    """
    Run Spot's LTL simplification on a formula string (equivalent to ltlfilt --simplify).
    Returns the simplified formula as a string.

    DEBUG NOTE (user request 2026-05-28):
    During active debugging of the reconstruction rules, do NOT invoke
    Spot rewriting. It hides the structure actually built by the labeler.
    This function is currently bypassed in the main reconstruction path.
    """
    if not formula_str or formula_str.startswith("UNSUPPORTED"):
        return formula_str

    # DEBUG MODE: Return raw formula to avoid Spot rewriting during debugging.
    # To re-enable Spot simplification, uncomment the block below.
    return formula_str

    # try:
    #     f = spot.formula(formula_str)
    #     simplified = f.simplify()
    #     return str(simplified)
    # except Exception as e:
    #     return f"{formula_str}   [simplification failed: {e}]"
