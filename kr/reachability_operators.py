"""
reachability_operators.py — Core 1-level (and future inductive) reachability K operators.

Extracted to a smaller module for easier manipulation and to keep the high-level
reconstruct logic in reachability.py small and focused.

These implement the base cases from Boker et al. for reset levels in the cascade.
"""

from __future__ import annotations
from typing import Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Guard helpers (valuation -> LTL prop formula string)
# ---------------------------------------------------------------------------

def letters_to_prop(valuation: Dict[str, bool], aps: List[str]) -> str:
    """Turn a valuation into a conjunction string like 'p & !q & r' for use in LTL."""
    parts = []
    for ap in aps:
        if valuation.get(ap, False):
            parts.append(ap)
        else:
            parts.append(f"!{ap}")
    return " & ".join(parts) if parts else "true"


def make_guard(valuations: List[Dict[str, bool]], aps: List[str], pred: Callable[[Dict[str, bool]], bool] = lambda v: True) -> str:
    """Build a disjunctive guard: OR of letters satisfying pred (default: all)."""
    good = [letters_to_prop(v, aps) for v in valuations if pred(v)]
    if not good:
        return "false"
    if len(good) == 1:
        return good[0]
    return "(" + " | ".join(good) + ")"


# ---------------------------------------------------------------------------
# 1-level base case reachability (following paper's K operators for reset)
#
# S, T, B are 1-based integer positions (coordinates) in the level.
# trans: Dict[letter_idx, target_pos]  -- the outgoing for *this* S only.
# tau: subformula to attach on arrival at T.
# ---------------------------------------------------------------------------

def one_level_reach_stay(
    S: int,
    B: Optional[int],
    T: int,
    tau: str,
    valuations: List[Dict[str, bool]],
    aps: List[str],
    trans: Dict[int, int],
) -> str:
    """Stay at S (or move within) until we take a letter to T, attaching tau."""
    stay_is = [i for i, tgt in trans.items() if tgt == S]
    stay_g = make_guard([valuations[i] for i in stay_is], aps) if stay_is else "false"
    to_T_is = [i for i, tgt in trans.items() if tgt == T]
    to_T_g = make_guard([valuations[i] for i in to_T_is], aps) if to_T_is else "false"

    if T == S:
        # Self case: typically G(stay) & tau or the U degenerates to tau if always can "enter"
        if to_T_g in ("false", "true") or not stay_g or stay_g == "true":
            return tau if (stay_g in ("false", "true") or not stay_g) else f"G({stay_g}) & ({tau})"
        return f"(({stay_g}) U (({to_T_g}) & ({tau})))"

    if to_T_g == "false":
        return "false"
    if stay_g == "false":
        return f"({to_T_g}) & ({tau})"
    return f"(({stay_g}) U (({to_T_g}) & ({tau})))"


def one_level_reach_strong(
    S: int,
    B: Optional[int],
    T: int,
    tau: str,
    valuations: List[Dict[str, bool]],
    aps: List[str],
    trans: Dict[int, int],
) -> str:
    """Strong reach: reach T from S while avoiding B (using the B param in guards)."""
    if B is None or B == 0:
        bad_g = "false"
    else:
        bad_letters = [i for i, tgt in trans.items() if tgt == B]
        bad_g = make_guard([valuations[i] for i in bad_letters], aps) if bad_letters else "false"

    base = one_level_reach_stay(S, B, T, tau, valuations, aps, trans)
    if bad_g == "false":
        return base

    # Strengthen the stay part to avoid bad
    stay_letters = [i for i, tgt in trans.items() if tgt == S]
    stay_g = make_guard([valuations[i] for i in stay_letters], aps) if stay_letters else "false"
    change_letters = [i for i, tgt in trans.items() if tgt == T]
    change_g = make_guard([valuations[i] for i in change_letters], aps) if change_letters else "false"

    safe_stay = f"(!({bad_g})) & ({stay_g})" if stay_g not in ("false", "true") else f"!({bad_g})"
    if change_g == "false":
        return "false"
    return f"(({safe_stay}) U (({change_g}) & ({tau})))"


def one_level_reach_weak(
    S: int,
    B: Optional[int],
    T: int,
    tau: str,
    valuations: List[Dict[str, bool]],
    aps: List[str],
    trans: Dict[int, int],
) -> str:
    """Weak (release-like) dual."""
    if B is None or B == 0:
        bad_g = "false"
    else:
        bad_letters = [i for i, tgt in trans.items() if tgt == B]
        bad_g = make_guard([valuations[i] for i in bad_letters], aps) if bad_letters else "false"

    stay_letters = [i for i, tgt in trans.items() if tgt == S]
    stay_g = make_guard([valuations[i] for i in stay_letters], aps) if stay_letters else "false"

    if bad_g == "false":
        return f"G( ({stay_g}) | ({tau}) )"
    return f"G( !({bad_g}) | ({tau}) )"  # placeholder; real dual should use release


def build_1level_reachability(
    S: int,
    B: Optional[int],
    T: int,
    tau: str,
    valuations: List[Dict[str, bool]],
    aps: List[str],
    trans_from_S: Dict[int, int],
) -> Dict[str, str]:
    """Convenience: return the family for this (S,B,T,tau)."""
    return {
        "strong": one_level_reach_strong(S, B, T, tau, valuations, aps, trans_from_S),
        "weak": one_level_reach_weak(S, B, T, tau, valuations, aps, trans_from_S),
        "stay_strong": one_level_reach_stay(S, B, T, tau, valuations, aps, trans_from_S),
    }


# Fin/Inf are still placeholders (will be expressed via the K ops in full version)
def fin_1level(C: int, valuations: List[Dict[str, bool]], aps: List[str], trans: Dict[int, int]) -> str:
    """Placeholder for Fin(C) = eventually escape C forever."""
    return f"F( G( ! at_config_{C} ) )"


def inf_1level(C: int, valuations: List[Dict[str, bool]], aps: List[str], trans: Dict[int, int]) -> str:
    """Placeholder for Inf(C) = G F visit C."""
    return f"G( F( at_config_{C} ) )"
