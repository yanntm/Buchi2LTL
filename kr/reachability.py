"""
reachability.py — Inductive LTL reachability operators on cascades (Boker et al. 2022).

Phase B start: 1-level (reset component) base cases.

For a 1-level cascade with positions (coordinates) 1..m :
- A "letter" is a valuation (dict prop->bool) or its index.
- Transitions are reset-like: from current pos, under a letter, you go to a (usually fixed) target pos.

The K operators describe controlled movement between positions while satisfying
propositional guards on the letters and a "tail" subformula τ.

This module provides the base-case formulas for depth 1. They reduce to
combinations of X, U, G, F, boolean combinations over the propositions.

The inductive case (multi-level) will combine these with sub-reachability on lower levels.
"""

from __future__ import annotations
from typing import Callable, Dict, List, Tuple, Any

# A "letter test" is a function (valuation: Dict[str,bool]) -> bool
# or we can use a string proposition formula, but for prototype we use python preds.

def letters_to_prop(valuation: Dict[str, bool], aps: List[str]) -> str:
    """Turn a valuation into a conjunction string like 'p & !q & r' for use in LTL."""
    parts = []
    for ap in aps:
        if valuation.get(ap, False):
            parts.append(ap)
        else:
            parts.append(f"!{ap}")
    return " & ".join(parts) if parts else "true"

def make_guard(valuations: List[Dict[str, bool]], aps: List[str], pred: Callable[[Dict[str,bool]], bool]) -> str:
    """Build a disjunctive guard: OR of letters satisfying pred."""
    good = [letters_to_prop(v, aps) for v in valuations if pred(v)]
    if not good:
        return "false"
    if len(good) == 1:
        return good[0]
    return "(" + " | ".join(good) + ")"

# ---------------------------------------------------------------------------
# 1-level base case reachability (following paper's 5 operators, simplified)
#
# For a single reset level, "S" and "T" are integers 1..m (the positions/coords).
# "B" is the bad position to avoid.
# τ is a sub-LTL (string) that must hold when we arrive at T.
#
# The operators describe paths that may stay at S or change level (but here level=pos).
# ---------------------------------------------------------------------------

def one_level_reach_stay(S: int, B: int, T: int, tau: str, valuations: List[Dict[str,bool]], aps: List[str],
                         trans: Dict[int, int]) -> str:
    """Base case for 'stay at top-level state S while moving to T' (strong version).

    In 1-level reset: stay letters from S are those where trans[li] == S.
    The "change" to T are letters where trans[li] == T.
    The formula is (stay_guard U (enter_T_guard & τ )) , with care for B.
    """
    stay_is = [i for i, tgt in trans.items() if tgt == S]
    stay_g = make_guard([valuations[i] for i in stay_is], aps, lambda v: True) if stay_is else "false"
    to_T_is = [i for i, tgt in trans.items() if tgt == T]
    to_T_g = make_guard([valuations[i] for i in to_T_is], aps, lambda v: True) if to_T_is else "false"
    if T == S:
        if to_T_g == "false" or to_T_g == "true":  # degenerate
            return f"G({stay_g}) & ({tau})" if stay_g not in ("false", "true") else tau
        return f"(({stay_g}) U (({to_T_g}) & ({tau})))"
    if to_T_g == "false":
        return "false"
    if stay_g == "false":
        return f"({to_T_g}) & ({tau})"
    return f"(({stay_g}) U (({to_T_g}) & ({tau})))"

def one_level_reach_strong(S: int, B: int, T: int, tau: str, valuations: List[Dict[str,bool]], aps: List[str],
                           trans: Dict[int, int]) -> str:
    """Strong version avoiding B entirely until arrival."""
    # Avoid B on the path
    # For 1-level, if B is a position, we avoid letters that would land in B before T.
    bad_letters = [i for i, tgt in trans.items() if tgt == B]
    bad_g = make_guard([valuations[i] for i in bad_letters], aps, lambda v: True) if bad_letters else "false"
    base = one_level_reach_stay(S, B, T, tau, valuations, aps, trans)
    if bad_g == "false":
        return base
    # Weaken to avoid bad: the until must not hit bad
    # Simplified: ( !bad & stay ) U (change & τ)
    stay_letters = [i for i, tgt in trans.items() if tgt == S]
    stay_g = make_guard([valuations[i] for i in stay_letters], aps, lambda v: True) if stay_letters else "false"
    change_letters = [i for i, tgt in trans.items() if tgt == T]
    change_g = make_guard([valuations[i] for i in change_letters], aps, lambda v: True) if change_letters else "false"
    safe_stay = f"(!({bad_g})) & ({stay_g})" if stay_g != "false" else f"!({bad_g})"
    if change_g == "false":
        return "false"
    return f"(({safe_stay}) U (({change_g}) & ({tau})))"

# Weak version (release style) can be dual: not ( strong to bad avoiding target )

def one_level_reach_weak(S: int, B: int, T: int, tau: str, valuations: List[Dict[str,bool]], aps: List[str],
                         trans: Dict[int, int]) -> str:
    """Weak (release) variant."""
    # ¬ ( S ~_B^X (¬τ) avoiding T )   or similar dual
    # For prototype: use the strong and negate appropriately, or direct.
    # Simple dual for 1-level:
    bad_letters = [i for i, tgt in trans.items() if tgt == B]
    bad_g = make_guard([valuations[i] for i in bad_letters], aps, lambda v: True) if bad_letters else "false"
    stay_letters = [i for i, tgt in trans.items() if tgt == S]
    stay_g = make_guard([valuations[i] for i in stay_letters], aps, lambda v: True) if stay_letters else "false"
    # "always avoid bad or have reached target with τ"
    if bad_g == "false":
        return f"G( ({stay_g}) | ({tau}) )"  # very rough
    return f"G( !({bad_g}) | ({tau}) )"  # placeholder; real dual per paper

# For the 5 variants in the paper (stay vs change, strong/weak, enter for change)
# The above are starting points. The enter/leave distinguish synchronous vs delayed attachment
# (similar to the tN sync/X logic in the old heuristic).

def build_1level_reachability(S: int, B: int, T: int, tau: str,
                              valuations: List[Dict[str, bool]], aps: List[str],
                              trans_from_S: Dict[int, int]) -> Dict[str, str]:
    """Return the family of reachability formulas for 1-level from S avoiding B to T with tail τ.
    Keys: 'strong', 'weak', 'strong_stay', etc. (expand as needed).
    """
    return {
        "strong": one_level_reach_strong(S, B, T, tau, valuations, aps, trans_from_S),
        "weak": one_level_reach_weak(S, B, T, tau, valuations, aps, trans_from_S),
        "stay_strong": one_level_reach_stay(S, B, T, tau, valuations, aps, trans_from_S),
    }

# Fin(C) / Inf(C) for a config C (for acceptance)
def fin_1level(C: int, valuations: List[Dict[str,bool]], aps: List[str],
               trans: Dict[int, int]) -> str:
    """Fin(C): C is visited only finitely often.
    Using the reachability: not ( from C can reach C infinitely often in a loop ).
    Simplified for 1-level: eventually we leave C forever (take a letter that goes elsewhere and stay out).
    """
    # Rough: F ( G ( not at C ) )
    # Better: there is a way to escape C and never return.
    # For prototype:
    return f"F( G( ! at_config_{C} ) )"  # placeholder syntax; in real we would use the K to say escape without return

def inf_1level(C: int, valuations: List[Dict[str,bool]], aps: List[str],
               trans: Dict[int, int]) -> str:
    """Inf(C): C visited i.o.  <=>  G F ( visit C ) """
    # Using reach: from any point, can always return to C
    return f"G( F( at_config_{C} ) )"  # again, placeholder; real uses the K operators

# Note: the real encoding uses the full K family to express "the run from initial config
# will satisfy the acceptance by visiting accepting configs i.o. under the right conditions".

if __name__ == "__main__":
    # Tiny self-test with data from G(p->(qUr))
    # Configs are (1,), (2,) but we treat as ints 1,2 for 1-level
    aps = ["p", "q", "r"]
    # From the run: for config 1 (state0?), trans under 0..7
    # From earlier test output, for (1,): mostly to (1,), letter 3 to (2,)
    # We map config 1->pos1, 2->pos2
    valuations = [ {'p':False,'q':False,'r':False}, {'p':True,'q':False,'r':False}, ... ] # truncated for test
    # In real use the ones from casc
    print("1-level reachability module loaded. Base cases ready for expansion.")
