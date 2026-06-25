"""
bls/operators/wreach.py — Formula 2: wreach (weak / release dual of reach).

    wreach(S, B, β, T, τ)  :=  ¬ reach(S, T, τ, B, β)     -- note the (B,β) ↔ (T,τ) swap

With no bad config the release antecedent never fires (vacuously true). The dual
yields the correct level-0 base case τ R ¬β automatically.
Reference: paper/automata-to-ltl-construction.md §7 Formula 2 (intended semantics §6 (2)).
"""

from __future__ import annotations
from typing import Optional, Tuple

import spot

from . import reach
from aut2ltl.ltl.builders import _tt, _ff, _to_f, _Not, _simp_f

def wreach(
    S: Tuple[int, ...],
    B: Optional[Tuple[int, ...]],
    beta: "str | spot.formula",
    T: Tuple[int, ...],
    tau: "str | spot.formula",
    casc: "Cascade",
    level: int = 0,
) -> "spot.formula":
    """Formula 2 (weak / release), literal dual per the paper:

        wreach(S, B, β, T, τ) := ¬ reach(S, T, τ, B, β)     -- (B,β) ↔ (T,τ) swap

    With no bad config the release antecedent never fires: vacuously true.
    The dual automatically yields the correct base case ¬((¬τ) U β).
    """
    if B is None:
        return _tt()
    tau_f = _tt() if tau is None else _to_f(tau)
    beta_f = _ff() if beta is None else _to_f(beta)
    inner = reach.reach(S, T, tau_f, B, beta_f, casc, level)
    return _simp_f(_Not(inner))

