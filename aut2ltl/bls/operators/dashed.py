"""
bls/operators/dashed.py — Formula 5: dashed (reach while the top state changes s ⤳ t).

dashed(⟨S,s⟩, ⟨B,b⟩, β, ⟨T,t⟩, τ): before reaching ⟨T,t⟩ the run reads an Enter(t)
letter switching the top state to t, then stays in t (via solid) and reaches ⟨T,t⟩
avoiding ⟨B,b⟩(β); line (3) forces it to actually Leave(s). Line (2) uses wsolid with
⟨B,b⟩ and ⟨T,t⟩ SWAPPED, so dashed stays co-safety (Σᵢ). The hardest of the five.
Reference: paper/automata-to-ltl-construction.md §7 Formula 5 (intended semantics §6 (5)).
"""

from __future__ import annotations
from typing import List, Optional, Tuple

import spot

from . import reach, solid, wsolid
from .support import (
    _memo_reach_helper, _combined_letters_at_level, _fuse_letters, _dedupe,
    TRACE_ON, _trace,
)
from aut2ltl.ltl.builders import _ff, _to_f, _And, _Or, _Not, _X, _simp_f, _short_f

@_memo_reach_helper("dc")
def dashed(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: "str | spot.formula", T: Tuple[int, ...], tau: "str | spot.formula", casc: "Cascade", level: int = 0
) -> "spot.formula":
    """Formula 5 (dashed / change top), per construction-ref §7:

      ⋁ over ⟨σ,T'⟩ ∈ Enter(t) :
        (  reach(S, S, false, T', σ ∧ X(solid(δ(⟨T',·⟩,σ), ⟨B,b⟩, β, ⟨T,t⟩, τ)))     -- line (1)
         ∧ ⋀ ⟨η,R⟩ ∈ Enter(b) :
              reach(S, R, η ∧ X(wsolid(δ(⟨R,·⟩,η), ⟨T,t⟩, τ, ⟨B,b⟩, β)),             -- line (2)
                    T', σ ∧ X(solid(δ(⟨T',·⟩,σ), ⟨B,b⟩, β, ⟨T,t⟩, τ)))                --  (swapped weak)
        )
      ∧ ⋁ over ⟨σ,L⟩ ∈ Leave(s) :
            solid(⟨S,s⟩, ⟨B,b⟩, β, ⟨L,s⟩, σ ∧ [¬β if ⟨L,s⟩=⟨B,b⟩])                    -- line (3)

    Notes:
    - No s == t guard: Table 1 only requires ∃-leave + ∃-enter (leave-and-return
      with s == t is a legitimate dashed path; Enter(q) ⊆ Stay(q) keeps it
      disjoint from solid via line (3)).
    - Enter(t)/Enter(b)/Leave(s) are combined letters ⟨σ, lower-config⟩
      enumerated over ALL h-image configs, not just from S — e.g. for G(a->Xb) no
      letter from the initial config enters the sink's top; entry fires only from
      the obligation state's lower config.
    - Lines (1)/(2) carry a lower-level prefix reach to T' (cursor level+1);
      δ(⟨T',·⟩,σ) is the observed arrival config of the entering letter
      (reset cascades: independent of the dropped layer state).
    - Line (1) is required separately for Enter(b) = ∅ (line (2) vacuous).
    """
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return reach.reach(S, B, beta, T, tau, casc, level)

    s_val = S[level]
    t_val = T[level]
    b_val = B[level] if B is not None else None
    beta_f = _to_f(beta)
    tau_f = _to_f(tau)

    cls = _combined_letters_at_level(casc, level)

    # Enter(q): genuine resets to q — witnessed by a pre-config whose layer
    # state differs from q (identity/stay letters never qualify: Enter ⊆ Stay).
    enter_t = _dedupe([(li, pre, arr) for (li, pre, arr) in cls
                       if pre[level] != t_val and arr[level] == t_val], level)
    enter_b = []
    if B is not None:
        enter_b = _dedupe([(li, pre, arr) for (li, pre, arr) in cls
                           if pre[level] != b_val and arr[level] == b_val], level)
    leave_s = _dedupe([(li, pre, arr) for (li, pre, arr) in cls
                       if pre[level] == s_val and arr[level] != s_val], level)

    _trace(f"    dashed level={level}: #enter_t={len(enter_t)} "
           f"#enter_b={len(enter_b)} #leave_s={len(leave_s)}")

    if not enter_t or not leave_s:
        # t never entered, or s never left: a dashed path is impossible.
        return _ff()

    # Letter fusion: enter groups read the arrival (inner solid/wsolid from
    # arr), so they fuse on (pre-suffix, arr); line-3 leaves fuse on pre only.
    enter_t_fused = _fuse_letters(enter_t, casc, level, with_arr=True)
    enter_b_fused = _fuse_letters(enter_b, casc, level, with_arr=True)
    leave_fused = _fuse_letters(leave_s, casc, level)

    entry_disjs_f: List[spot.formula] = []
    for g_f, pre, arr in enter_t_fused:
        # inner: after entering t at config arr, solid-stay at t to reach ⟨T,t⟩(τ)
        inner_f = solid.solid(arr, B, beta_f, T, tau_f, casc, level)
        tail_f = _simp_f(_And(g_f, _X(inner_f)))
        # line (1): freely reach the firing lower config T', then enter + stay
        line_parts_f: List[spot.formula] = [
            reach.reach(S, None, _ff(), pre, tail_f, casc, level + 1)
        ]
        # line (2): same reach, but parameterized-bad on each potential entry into b:
        # never be about to enter b (η firing) with a weak-stay-at-b that reaches
        # ⟨B,b⟩(β) unreleased by ⟨T,t⟩(τ)  — the SWAPPED wsolid call per the paper.
        for eta_f, preR, arrR in enter_b_fused:
            # Narrowly skip entries with no valid weak form; a broad `except`
            # would mask real errors and test-harness control exceptions.
            try:
                wsolid_sw = wsolid.wsolid(arrR, T, tau_f, B, beta_f, casc, level)
            except (ValueError, IndexError, KeyError):
                continue
            bbeta_f = _simp_f(_And(eta_f, _X(wsolid_sw)))
            line_parts_f.append(
                reach.reach(S, preR, bbeta_f, pre, tail_f, casc, level + 1)
            )
        entry_disjs_f.append(_And(*line_parts_f))

    lines12_f = _Or(*entry_disjs_f) if entry_disjs_f else _ff()

    # line (3): the layer state is indeed changed — solid-stay (avoiding bad)
    # up to the moment a Leave letter fires (target = the leave firing point
    # ⟨L,s⟩; does NOT force an immediate change).
    line3_parts_f: List[spot.formula] = []
    for lg_f, preL, arrL in leave_fused:
        tail_f = lg_f
        if B is not None and preL[level:] == B[level:] and not beta_f.is_ff():
            tail_f = _And(lg_f, _Not(beta_f))
        line3_parts_f.append(solid.solid(S, B, beta_f, preL, tail_f, casc, level))
    line3_f = _Or(*line3_parts_f) if line3_parts_f else _ff()

    return _simp_f(_And(lines12_f, line3_f))

