"""
bls/operators/wsolid.py — Formula 4: wsolid (the weak version of solid).

wsolid(⟨S,s⟩, ⟨B,b⟩, β, ⟨T,t⟩, τ): reaching ⟨T,t⟩(τ) releases not (reaching ⟨B,b⟩(β) or
leaving s). Same four-case shape as solid but the 4th case differs ((Q ∨ τ) ∧ ¬β, not
solid's (P ∧ ¬β) ∨ τ), and the core `wsolid_plus` (wsolid⁺) uses `wreach`: line (1)
mirrors solid⁺ without the free-reach conjunct (weak ⇒ reaching is optional); line (2)
stays in s forever, never blocked (target false).
Reference: paper/automata-to-ltl-construction.md §7 Formula 4 (intended semantics §6 (4)).
"""

from __future__ import annotations
from typing import List, Optional, Tuple

import spot

from . import wreach
from .support import (
    _memo_reach_helper, _combined_letters_at_level, _fuse_letters, _dedupe,
    TRACE_ON, _trace,
)
from aut2ltl.ltl.builders import _tt, _ff, _to_f, _And, _Or, _Not, _X, _simp_f, _short_f

@_memo_reach_helper("ws")
def wsolid(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: "str | spot.formula", T: Tuple[int, ...], tau: "str | spot.formula", casc: "Cascade", level: int = 0
) -> "spot.formula":
    """Formula 4 (weak solid/stay). Mirror of strong but uses weak subs + slightly different case ors."""
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return wreach.wreach(S, B, beta, T, tau, casc, level)

    s_val = S[level]
    t_val = T[level]
    b_val = B[level] if B is not None else None
    source_is_bad = (B is not None and S[level:] == B[level:])
    source_is_target = (S[level:] == T[level:])

    # NO s_val != t_val early-false here (valid only for the STRONG solid):
    # with an unreachable target the weak formula degrades to "never blocked"
    # — wsolid⁺ line (1) simply gets no candidates and line (2) survives.

    beta_f = _to_f(beta)
    tau_f = _to_f(tau)
    gt0_f = wsolid_plus(S, B, beta_f, T, tau_f, casc, level)

    if not source_is_bad and not source_is_target:
        return gt0_f
    elif not source_is_bad and source_is_target:
        # S != B and S == T: gt0 ∨ τ  (gt0 already carries the full weak line1+line2).
        return _simp_f(_Or(gt0_f, tau_f))
    elif source_is_bad and not source_is_target:
        return _simp_f(_And(gt0_f, _Not(beta_f)))
    else:
        # Case 4 (weak form): (gt0 ∨ τ) ∧ ¬β  (differs from solid's (gt0 ∧ ¬β) ∨ τ).
        return _simp_f(_And( _Or(gt0_f, tau_f) , _Not(beta_f) ))



@_memo_reach_helper("ws0")
def wsolid_plus(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: "str | spot.formula", T: Tuple[int, ...], tau: "str | spot.formula", casc: "Cascade", level: int = 0
) -> "spot.formula":
    """wsolid⁺ (the >0 common subformula of Formula 4), per construction-ref §7:

      -- line (1): eventually reach ⟨T,t⟩, still staying in s
      ⋁ ⟨σ,T'⟩ ∈ Stay(s) with δ(⟨T',s⟩,σ) = ⟨T,t⟩ :
          ⋀ ⟨η,L⟩ ∈ Leave(s) :   wreach(S, L, η, T', σ ∧ Xτ)
        ∧ ⋀ ⟨ρ,B'⟩ ∈ Stay(s), δ(⟨B',s⟩,ρ)=⟨B,b⟩ : wreach(S, B', ρ ∧ Xβ, T', σ ∧ Xτ)
      ∨
      -- line (2): never reach ⟨T,t⟩; stay in s forever, never blocked
          ⋀ ⟨η,L⟩ ∈ Leave(s) :   wreach(S, L, η, S, false)
        ∧ ⋀ ⟨ρ,B'⟩ ∈ Stay(s), δ(⟨B',s⟩,ρ)=⟨B,b⟩ : wreach(S, B', ρ ∧ Xβ, S, false)

    Line (1) is wsolid⁺'s solid⁺ analogue WITHOUT the free-reach conjunct
    (weak ⇒ reaching is optional); all avoids use wreach. Line (2) uses
    target false: wreach(…, S, false) means "never trigger the avoid", i.e.
    stay forever unblocked. Combined letters enumerated over all h-image
    configs (not just from S).
    """
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return wreach.wreach(S, B, beta, T, tau, casc, level)

    beta_f = _to_f(beta)
    tau_f = _to_f(tau)
    s_val = S[level]

    cls = _combined_letters_at_level(casc, level)

    stay_s = _dedupe([(li, pre, arr) for (li, pre, arr) in cls
                      if pre[level] == s_val and arr[level] == s_val], level)
    leave_s = _dedupe([(li, pre, arr) for (li, pre, arr) in cls
                       if pre[level] == s_val and arr[level] != s_val], level)
    last_steps = [(li, pre, arr) for (li, pre, arr) in stay_s if arr[level:] == T[level:]]
    bad_pre = []
    if B is not None:
        bad_pre = [(li, pre, arr) for (li, pre, arr) in stay_s if arr[level:] == B[level:]]

    _trace(f"    wsolid_plus level={level}: #stay={len(stay_s)} #leave={len(leave_s)} "
           f"#last_steps={len(last_steps)} #bad_pre={len(bad_pre)}")

    # Letter fusion: one summand per outcome class, guards OR-ed.
    last_fused = _fuse_letters(last_steps, casc, level)
    leave_fused = _fuse_letters(leave_s, casc, level)
    bad_fused = _fuse_letters(bad_pre, casc, level)

    def _avoid_conjs(target_cfg: Tuple[int, ...], tail_f: "spot.formula") -> List[spot.formula]:
        conjs: List[spot.formula] = []
        for eta_f, preL, arrL in leave_fused:
            conjs.append(wreach.wreach(S, preL, eta_f, target_cfg, tail_f, casc, level + 1))
        for rho_f, preB, arrB in bad_fused:
            rb_f = _simp_f(_And(rho_f, _X(beta_f)))
            conjs.append(wreach.wreach(S, preB, rb_f, target_cfg, tail_f, casc, level + 1))
        return conjs

    # line (1)
    line1_disjs_f: List[spot.formula] = []
    for g_f, pre, arr in last_fused:
        tail_f = _simp_f(_And(g_f, _X(tau_f)))
        conjs = _avoid_conjs(pre, tail_f)
        line1_disjs_f.append(_And(*conjs) if conjs else _tt())
    line1_f = _Or(*line1_disjs_f) if line1_disjs_f else _ff()

    # line (2): stay forever, never blocked (target false never claimed)
    line2_conjs = _avoid_conjs(S, _ff())
    line2_f = _And(*line2_conjs) if line2_conjs else _tt()

    res_f = _simp_f(_Or(line1_f, line2_f))
    if TRACE_ON:
        _trace(f"    wsolid_plus (wsolid+) res={_short_f(res_f, 60)}")
    return res_f

