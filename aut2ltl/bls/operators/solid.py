"""
bls/operators/solid.py — Formula 3: solid (reach while the top-level state stays s).

solid(⟨S,s⟩, ⟨B,b⟩, β, ⟨T,t⟩, τ): reach ⟨T,t⟩(τ) while the level's state never leaves
s (so it forces t = s). Four cases on whether the source equals the bad and/or target
config, over the nonempty-prefix core `solid_plus` (solid⁺). solid_plus recurses to
`reach` at the LOWER level over the Stay(s)/Leave(s) combined-letter partition.
Reference: paper/automata-to-ltl-construction.md §7 Formula 3 (intended semantics §6 (3)).
"""

from __future__ import annotations
from typing import List, Optional, Tuple

import spot

from . import reach
from .support import (
    _memo_reach_helper, _combined_letters_at_level, _fuse_letters, _dedupe,
    TRACE_ON, _trace,
)
from aut2ltl.ltl.builders import _tt, _ff, _to_f, _And, _Or, _Not, _X, _simp_f, _short_f

@_memo_reach_helper("ss")
def solid(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: "str | spot.formula", T: Tuple[int, ...], tau: "str | spot.formula", casc: "Cascade", level: int = 0
) -> "spot.formula":
    """Formula 3 (strong solid / stay, top unchanged). Cases on the current level's
    coord. Formula objects in and out (str accepted for probe/test compat)."""
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return reach.reach(S, B, beta, T, tau, casc, level)

    beta_f = _to_f(beta)
    tau_f = _to_f(tau)

    s_val = S[level]
    t_val = T[level]
    # Paper Formula 3 cases compare FULL configs ⟨S,s⟩ vs ⟨B,b⟩ / ⟨T,t⟩.
    source_is_bad = (B is not None and S[level:] == B[level:])
    source_is_target = (S[level:] == T[level:])

    if s_val != t_val:
        _trace(f"  solid level={level}: s_val({s_val}) != t_val({t_val}) -> solid impossible, return false")
        return _ff()

    _trace(f"  solid level={level}: source_is_target={source_is_target} source_is_bad={source_is_bad}")

    # Immediate collapse for tau=true target (Formula 3: P ∨ true / (P∧¬β) ∨ true)
    if source_is_target and tau_f.is_tt():
        return _tt()

    gt0_f = solid_plus(S, B, beta_f, T, tau_f, casc, level)

    if not source_is_bad and not source_is_target:
        return gt0_f
    elif not source_is_bad and source_is_target:
        return _simp_f(_Or(gt0_f, tau_f))
    elif source_is_bad and not source_is_target:
        return _simp_f(_And(gt0_f, _Not(beta_f)))
    else:
        return _simp_f(_Or( _And(gt0_f, _Not(beta_f)) , tau_f ))


@_memo_reach_helper("ss0")
def solid_plus(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: "str | spot.formula", T: Tuple[int, ...], tau: "str | spot.formula", casc: "Cascade", level: int = 0
) -> "spot.formula":
    """solid⁺ (the >0 common subformula of Formula 3), per construction-ref §7:

      ⋁ over ⟨σ,T'⟩ ∈ Stay(s) with δ(⟨T',s⟩,σ) = ⟨T,t⟩ :
          reach(S, S, false, T', σ ∧ Xτ)                       -- freely reach the pre-target T'
        ∧ ⋀ ⟨η,L⟩ ∈ Leave(s) :   reach(S, L, η, T', σ ∧ Xτ)    -- never about to fire a Leave first
        ∧ ⋀ ⟨ρ,B'⟩ ∈ Stay(s), δ(⟨B',s⟩,ρ)=⟨B,b⟩ :
                                  reach(S, B', ρ ∧ Xβ, T', σ ∧ Xτ)  -- never step into bad first

    Last-step decomposition: the lower level reaches the firing point T', the
    stay-in-s constraint is enforced by the Leave-avoid conjuncts, recursion is
    strictly to level+1. Combined letters are enumerated over all h-image
    configs (not just from S).
    """
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return reach.reach(S, B, beta, T, tau, casc, level)

    beta_f = _to_f(beta)
    tau_f = _to_f(tau)
    s_val = S[level]

    cls = _combined_letters_at_level(casc, level)
    # Stay(s)/Leave(s): combined letters observed from layer state s.
    stay_s = [(li, pre, arr) for (li, pre, arr) in cls if pre[level] == s_val and arr[level] == s_val]
    leave_s = [(li, pre, arr) for (li, pre, arr) in cls if pre[level] == s_val and arr[level] != s_val]

    stay_s = _dedupe(stay_s, level)
    leave_s = _dedupe(leave_s, level)

    # Last-step candidates: ⟨σ,T'⟩ ∈ Stay(s) whose firing lands exactly on T (from `level` down).
    last_steps = [(li, pre, arr) for (li, pre, arr) in stay_s if arr[level:] == T[level:]]

    # Bad-predecessor steps: ⟨ρ,B'⟩ ∈ Stay(s) whose firing lands exactly on B.
    bad_pre = []
    if B is not None:
        bad_pre = [(li, pre, arr) for (li, pre, arr) in stay_s if arr[level:] == B[level:]]

    _trace(f"    solid_plus level={level}: #stay={len(stay_s)} #leave={len(leave_s)} "
           f"#last_steps={len(last_steps)} #bad_pre={len(bad_pre)}")

    # Letter fusion: one summand per outcome class, guards OR-ed (the
    # avoid groups fuse by pre-config only — their summand never reads arr).
    last_fused = _fuse_letters(last_steps, casc, level)
    leave_fused = _fuse_letters(leave_s, casc, level)
    bad_fused = _fuse_letters(bad_pre, casc, level)

    disjs_f: List[spot.formula] = []
    for g_f, pre, arr in last_fused:
        tail_f = _simp_f(_And(g_f, _X(tau_f)))
        conj_f: List[spot.formula] = []
        # free reach of the pre-target T' (bad never triggers: beta=false)
        conj_f.append(reach.reach(S, None, _ff(), pre, tail_f, casc, level + 1))
        # Leave-avoid conjuncts
        for eta_f, preL, arrL in leave_fused:
            conj_f.append(reach.reach(S, preL, eta_f, pre, tail_f, casc, level + 1))
        # bad-predecessor conjuncts
        for rho_f, preB, arrB in bad_fused:
            rb_f = _simp_f(_And(rho_f, _X(beta_f)))
            conj_f.append(reach.reach(S, preB, rb_f, pre, tail_f, casc, level + 1))
        disjs_f.append(_And(*conj_f))

    res_f = _simp_f(_Or(*disjs_f)) if disjs_f else _ff()
    if TRACE_ON:
        _trace(f"    solid_plus result level={level}: {_short_f(res_f, 80)}")
    return res_f

