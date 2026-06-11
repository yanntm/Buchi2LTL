"""
reachability_operators.py — The five inductive reachability formulas.

Implements the 5 reachability formulas (strong/weak, solid-stay/dashed-change,
with >0 variants) from Boker et al. paper Sec 4.2 (see
paper/automata-to-ltl-construction.md §7; ground truth paper/Automata2LTL.txt).
The formulas are mutually recursive (well-founded on cascade level) and are kept
together in this module on purpose — they are one technical unit.

Leaf utilities (guards, simplify, spot.formula builders) live in kr/ltl_builders.py.
Fin(C) (Lemma 7) lives in kr/fin.py (imports this module one-way).
The high-level assembly (Fin + Muller DNF) lives in kr/reachability.py.

All driven uniformly by Cascade config transitions and letter valuations (no patterns
on the automaton shape; the normalized det aut in the Cascade *is* the working D).
Module-level state (PAPER_* counters, _reach_memo, casc registry) is reset by
reconstruct_ltl_paper_style before each build; tests reset/read it via this module.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import os
from functools import lru_cache

# ---------------------------------------------------------------------------
# Debug / tracing support (enable with KR_TRACE=1 env var for verbose construction traces)
# This is invaluable during development of the inductive reachability formulas.
# Traces show level-by-level decisions, stay/leave partitions, sub-formula construction, etc.
# Set TRACE_ON = True below or use the env var. Can be removed/refined post-dev.
# ---------------------------------------------------------------------------
TRACE_ON = os.getenv("KR_TRACE", "0").lower() in ("1", "true", "yes", "on")

# Instrumentation counters (for profiling blowups / possible infinite construction loops).
# Incremented from reach_strong and fin_c. Exposed so callers/tests can read/print.
PAPER_REACH_CALLS = 0
PAPER_FIN_CALLS = 0
PAPER_MAX_LTL_SIZE = 0

# Simple memo for reach_strong subproblems during one construction.
# Key includes id(casc) for safety. Acts as "unique table of visited" to avoid
# exponential re-expansion of identical (S, B, beta, T, tau, level) subformulas.
# This should prevent the work explosion that looks like "infinite loop".
_reach_memo = {}

# For lru on R* (arch adoption): registry to allow passing only hashable cid to cached funcs.
# Cleared in reconstruct before each top-level build.
_casc_by_id: Dict[int, "Cascade"] = {}

def _register_casc(casc: "Cascade") -> int:
    cid = id(casc)
    _casc_by_id[cid] = casc
    return cid

def _get_casc(cid: int) -> Optional["Cascade"]:
    return _casc_by_id.get(cid)

def _clear_casc_registry():
    _casc_by_id.clear()

def _trace(msg: str) -> None:
    if TRACE_ON:
        print("[KR] " + msg)

# Guard helpers, simplification, and native spot.formula builders live in
# kr/ltl_builders.py (no kr deps). Re-imported here under their original names;
# letters_to_prop / make_guard / simplify_ltl / normalize_ltl stay importable
# from this module for compat.
from kr.ltl_builders import (
    letters_to_prop,
    make_guard,
    simplify_ltl,
    normalize_ltl,
    _normalize_ltl,
    _tt, _ff, _ap, _And, _Or, _Not, _X, _U, _F, _G,
    _to_f, _letters_to_f, _str_f,
)

# Fin(C) (Lemma 7) lives in kr/fin.py (one-way dependency: fin imports this
# module, never the reverse). Import fin_c from kr.fin directly.




import spot  # used for formula types in signatures and lru keys

# ---------------------------------------------------------------------------
# Generalized inductive reachability (the 5 formulas, per kr/algorithm.md + paper Sec 4.2)
# These recurse on config tuple length (level). Base case when level == num_levels
# (empty suffix): plain Until (paper's level 0 on the empty configuration).
# All driven by cascade's move_config + letter_valuations (algebraic, no pattern match on orig aut).
# ---------------------------------------------------------------------------

def reach_strong(
    S: Tuple[int, ...],
    B: Optional[Tuple[int, ...]],
    beta: str,
    T: Tuple[int, ...],
    tau: str,
    casc: "Cascade",
    level: int = 0,
) -> str:
    """Formula 1 (main strong): S ~_B(β)^X T(τ) at the given cascade level (coordinate index).

    Recursion advances the level cursor while always passing full-length config tuples
    (so move_config and partition helpers always see correct context for higher coords).
    Base: when level == num_levels, plain (¬β) U τ .

    Now leverages native spot.formula for internal construction (DAG sharing via object identity,
    better subformula reuse, lru potential, less string roundtrips). Public returns str for compat.
    Beta/tau normalized to formula objects early.
    Uses lru_cache on _lru_reach_strong (with cid for hashability).
    """
    global PAPER_REACH_CALLS
    PAPER_REACH_CALLS += 1
    if PAPER_REACH_CALLS > 100000:
        raise RuntimeError("Too many reach_strong calls (>100k) -- likely explosion from lack of memoization on sub-reach or infinite rec on same-level moves")

    # Convert to native formulas early (architectural adoption: spot.formula DAG)
    beta_f = _to_f(beta or "false")
    tau_f = _to_f(tau or "true")

    cid = id(casc)
    _register_casc(casc)

    # lru lookup (keyed on hashables: cid + tuples + formula objs; B can be None, which is hashable)
    res = _lru_reach_strong(cid, S, B, beta_f, T, tau_f, level)

    # keep old memo for any legacy code / traces
    key = (S, B if B is not None else (), beta_f, T, tau_f, level, cid)
    _reach_memo[key] = res
    return res


@lru_cache(maxsize=None)
def _lru_reach_strong(cid: int, S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta_f: 'spot.formula', T: Tuple[int, ...], tau_f: 'spot.formula', level: int) -> str:
    """Core cached implementation of reach_strong. Args are all hashable (B=None ok)."""
    casc = _get_casc(cid)
    if casc is None:
        return "false"

    n = getattr(casc, "num_levels", 0)
    if level == n:
        negb = _tt() if str(beta_f) in ("false", "0") else _Not(beta_f)
        res_f = _U(negb, tau_f)
        res = _str_f(res_f)
        _trace(f"base level reached (level={level}): returning {res}")
        return res

    _trace(f"reach_strong level={level}/{n} S={S} T={T} beta={_str_f(beta_f)} tau={_str_f(tau_f)}")

    # 0-step only for trivial tau=true
    suffix_S = S[level:]
    suffix_T = T[level:]
    if suffix_S == suffix_T and str(tau_f) == "true":
        _trace(f"  suffix from level {level} already matches target -> return tau early")
        return "true"

    # Current level's value (for solid/dashed decision at this layer)
    s_val = S[level]
    t_val = T[level]
    b_val = B[level] if B is not None else None
    source_is_target = (suffix_S == suffix_T)
    source_is_bad = (B is not None and s_val == b_val)

    _trace(f"  at level {level}: s_val={s_val} t_val={t_val} source_is_target={source_is_target} source_is_bad={source_is_bad}")

    # helpers accept str for compat during transition
    solid = _solid_stay_strong(S, B, _str_f(beta_f), T, _str_f(tau_f), casc, level)
    dashed = _dashed_change_strong(S, B, _str_f(beta_f), T, _str_f(tau_f), casc, level)
    _trace(f"    solid={solid[:120]}{'...' if len(solid)>120 else ''}")
    _trace(f"    dashed={dashed[:120]}{'...' if len(dashed)>120 else ''}")

    # Build final with formula for sharing, then str
    res_f = _Or( _to_f(solid), _to_f(dashed) )
    res = _str_f(res_f)
    _trace(f"    reach_strong res (pre-memo, post-simp)={res[:150]}{'...' if len(res)>150 else ''}")
    return res


def reach_weak(
    S: Tuple[int, ...],
    B: Optional[Tuple[int, ...]],
    beta: str,
    T: Tuple[int, ...],
    tau: str,
    casc: "Cascade",
    level: int = 0,
) -> str:
    """Formula 2 (weak / release), literal dual per the paper:

        wreach(S, B, β, T, τ) := ¬ reach(S, T, τ, B, β)     -- (B,β) ↔ (T,τ) swap

    With no bad config the release antecedent never fires: vacuously true.
    The dual automatically yields the correct base case ¬((¬τ) U β).
    (The previous bespoke G(τ | ¬β) base was wrong — Table 1 formula 2 at
    level 0 is exactly τ R ¬β — and the bespoke solid_w ∨ dashed_w
    construction was not the paper's Formula 2.)
    """
    if B is None:
        return "true"
    inner = reach_strong(S, T, tau or "true", B, beta or "false", casc, level)
    return simplify_ltl(f"!({inner})")


def _solid_stay_strong(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade", level: int = 0
) -> str:
    """Formulas 3 (strong solid/stay top unchanged). Cases on current level's coord.
    Internals now use spot.formula builders for construction.
    """
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return reach_strong(S, B, beta, T, tau, casc, level)

    beta_f = _to_f(beta)
    tau_f = _to_f(tau)

    s_val = S[level]
    t_val = T[level]
    # Paper Formula 3 cases compare FULL configs ⟨S,s⟩ vs ⟨B,b⟩ / ⟨T,t⟩.
    source_is_bad = (B is not None and S[level:] == B[level:])
    source_is_target = (S[level:] == T[level:])

    if s_val != t_val:
        _trace(f"  _solid_stay_strong level={level}: s_val({s_val}) != t_val({t_val}) -> solid impossible, return false")
        return "false"

    _trace(f"  _solid_stay_strong level={level}: source_is_target={source_is_target} source_is_bad={source_is_bad}")

    # Immediate collapse for tau=true target (Formula 3: P ∨ true / (P∧¬β) ∨ true)
    if source_is_target and str(tau_f) == "true":
        return "true"

    gt0 = _stay_gt0_strong(S, B, _str_f(beta_f), T, _str_f(tau_f), casc, level)
    gt0_f = _to_f(gt0)

    if not source_is_bad and not source_is_target:
        return _str_f(gt0_f)
    elif not source_is_bad and source_is_target:
        res_f = _Or(gt0_f, tau_f)
        return _str_f(res_f)
    elif source_is_bad and not source_is_target:
        res_f = _And(gt0_f, _Not(beta_f))
        return _str_f(res_f)
    else:
        res_f = _Or( _And(gt0_f, _Not(beta_f)) , tau_f )
        return _str_f(res_f)


def _combined_letters_at_level(casc: "Cascade", level: int) -> List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]]:
    """Observable combined letters at layer `level`: list of (li, pre, arrived)
    over every h-image config `pre` and letter li. The paper's combined letter
    ⟨σ, L⟩ for this layer corresponds to (li, pre[level+1:]); pre[level] is the
    layer state it is observed from. Enumerating h-image configs is the
    observable approximation of the full product cascade (exact when h covers
    the reachable configs, which decompose_aut's state_to_config provides).
    """
    out: List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]] = []
    for pre in casc.all_configs():
        if len(pre) <= level:
            continue
        for li in range(casc.num_letters()):
            try:
                arr = casc.move_config(pre, li)
            except Exception:
                continue
            if li >= len(casc.letter_valuations):
                continue
            out.append((li, pre, arr))
    return out


def _stay_gt0_strong(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade", level: int = 0
) -> str:
    """solid⁺ (the >0 common subformula of Formula 3), literal per paper p.11 /
    construction-ref §7:

      ⋁ over ⟨σ,T'⟩ ∈ Stay(s) with δ(⟨T',s⟩,σ) = ⟨T,t⟩ :
          reach(S, S, false, T', σ ∧ Xτ)                       -- freely reach the pre-target T'
        ∧ ⋀ ⟨η,L⟩ ∈ Leave(s) :   reach(S, L, η, T', σ ∧ Xτ)    -- never about to fire a Leave first
        ∧ ⋀ ⟨ρ,B'⟩ ∈ Stay(s), δ(⟨B',s⟩,ρ)=⟨B,b⟩ :
                                  reach(S, B', ρ ∧ Xβ, T', σ ∧ Xτ)  -- never step into bad first

    Last-step decomposition: the lower level reaches the firing point T', the
    stay-in-s constraint is enforced by the Leave-avoid conjuncts, recursion is
    strictly to level+1. Combined letters are enumerated over all h-image
    configs (not just from S) — the from-S evaluation was the 2L breaker.
    """
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return reach_strong(S, B, beta, T, tau, casc, level)

    beta_f = _to_f(beta)
    tau_f = _to_f(tau)
    s_val = S[level]

    cls = _combined_letters_at_level(casc, level)
    # Stay(s)/Leave(s): combined letters observed from layer state s.
    stay_s = [(li, pre, arr) for (li, pre, arr) in cls if pre[level] == s_val and arr[level] == s_val]
    leave_s = [(li, pre, arr) for (li, pre, arr) in cls if pre[level] == s_val and arr[level] != s_val]

    # Dedupe by the paper's combined-letter identity (li, lower-config suffix).
    def _dedupe(triples):
        seen = {}
        for li, pre, arr in triples:
            key = (li, pre[level + 1:])
            if key not in seen:
                seen[key] = (li, pre, arr)
        return list(seen.values())

    stay_s = _dedupe(stay_s)
    leave_s = _dedupe(leave_s)

    # Last-step candidates: ⟨σ,T'⟩ ∈ Stay(s) whose firing lands exactly on T (from `level` down).
    last_steps = [(li, pre, arr) for (li, pre, arr) in stay_s if arr[level:] == T[level:]]

    # Bad-predecessor steps: ⟨ρ,B'⟩ ∈ Stay(s) whose firing lands exactly on B.
    bad_pre = []
    if B is not None:
        bad_pre = [(li, pre, arr) for (li, pre, arr) in stay_s if arr[level:] == B[level:]]

    _trace(f"    _stay_gt0_strong level={level}: #stay={len(stay_s)} #leave={len(leave_s)} "
           f"#last_steps={len(last_steps)} #bad_pre={len(bad_pre)}")

    disjs_f: List[spot.formula] = []
    for li, pre, arr in last_steps:
        g_f = _letters_to_f(casc.letter_valuations[li], casc.aps)
        if str(g_f) == "false":
            continue
        tail_f = _And(g_f, _X(tau_f))
        tail = _str_f(tail_f)
        conj_f: List[spot.formula] = []
        # free reach of the pre-target T' (bad never triggers: beta=false)
        conj_f.append(_to_f(reach_strong(S, None, "false", pre, tail, casc, level + 1)))
        # Leave-avoid conjuncts
        for lj, preL, arrL in leave_s:
            eta_f = _letters_to_f(casc.letter_valuations[lj], casc.aps)
            if str(eta_f) == "false":
                continue
            conj_f.append(_to_f(reach_strong(S, preL, _str_f(eta_f), pre, tail, casc, level + 1)))
        # bad-predecessor conjuncts
        for lk, preB, arrB in bad_pre:
            rho_f = _letters_to_f(casc.letter_valuations[lk], casc.aps)
            if str(rho_f) == "false":
                continue
            rb_f = _And(rho_f, _X(beta_f))
            conj_f.append(_to_f(reach_strong(S, preB, _str_f(rb_f), pre, tail, casc, level + 1)))
        disjs_f.append(_And(*conj_f))

    res_f = _Or(*disjs_f) if disjs_f else _ff()
    res = _str_f(res_f)
    _trace(f"    _stay_gt0 result level={level}: {res[:80]}...")
    return res


def _solid_stay_weak(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade", level: int = 0
) -> str:
    """Formula 4 (weak solid/stay). Mirror of strong but uses weak subs + slightly different case ors."""
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return reach_weak(S, B, beta, T, tau, casc, level)

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
    gt0 = _stay_gt0_weak(S, B, _str_f(beta_f), T, _str_f(tau_f), casc, level)
    gt0_f = _to_f(gt0)

    if not source_is_bad and not source_is_target:
        return _str_f(gt0_f)
    elif not source_is_bad and source_is_target:
        # Per ref Rws case (S != B and S == T): exactly Rws0 ∨ τ  (gt0 already carries the full weak line1+line2)
        # (Removed special stay_prop U path -- was bypassing gt0/line2 and had dead source_is_bad test inside not-bad branch.)
        res_f = _Or(gt0_f, tau_f)
        return _str_f(res_f)
    elif source_is_bad and not source_is_target:
        res_f = _And(gt0_f, _Not(beta_f))
        return _str_f(res_f)
    else:
        # Case 4 per corrected paper (weak form): (Rws0 ∨ τ) ∧ ¬β
        res_f = _And( _Or(gt0_f, tau_f) , _Not(beta_f) )
        return _str_f(res_f)


def _stay_gt0_weak(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade", level: int = 0
) -> str:
    """wsolid⁺ (the >0 common subformula of Formula 4), literal per paper p.12 /
    construction-ref §7:

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
    configs (the from-S evaluation was the 2L breaker).
    """
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return reach_weak(S, B, beta, T, tau, casc, level)

    beta_f = _to_f(beta)
    tau_f = _to_f(tau)
    s_val = S[level]

    cls = _combined_letters_at_level(casc, level)

    def _dedupe(triples):
        seen = {}
        for li, pre, arr in triples:
            key = (li, pre[level + 1:])
            if key not in seen:
                seen[key] = (li, pre, arr)
        return list(seen.values())

    stay_s = _dedupe([(li, pre, arr) for (li, pre, arr) in cls
                      if pre[level] == s_val and arr[level] == s_val])
    leave_s = _dedupe([(li, pre, arr) for (li, pre, arr) in cls
                       if pre[level] == s_val and arr[level] != s_val])
    last_steps = [(li, pre, arr) for (li, pre, arr) in stay_s if arr[level:] == T[level:]]
    bad_pre = []
    if B is not None:
        bad_pre = [(li, pre, arr) for (li, pre, arr) in stay_s if arr[level:] == B[level:]]

    _trace(f"    _stay_gt0_weak level={level}: #stay={len(stay_s)} #leave={len(leave_s)} "
           f"#last_steps={len(last_steps)} #bad_pre={len(bad_pre)}")

    def _avoid_conjs(target_cfg: Tuple[int, ...], tail: str) -> List[spot.formula]:
        conjs: List[spot.formula] = []
        for lj, preL, arrL in leave_s:
            eta_f = _letters_to_f(casc.letter_valuations[lj], casc.aps)
            if str(eta_f) == "false":
                continue
            conjs.append(_to_f(reach_weak(S, preL, _str_f(eta_f), target_cfg, tail, casc, level + 1)))
        for lk, preB, arrB in bad_pre:
            rho_f = _letters_to_f(casc.letter_valuations[lk], casc.aps)
            if str(rho_f) == "false":
                continue
            rb = _str_f(_And(rho_f, _X(beta_f)))
            conjs.append(_to_f(reach_weak(S, preB, rb, target_cfg, tail, casc, level + 1)))
        return conjs

    # line (1)
    line1_disjs_f: List[spot.formula] = []
    for li, pre, arr in last_steps:
        g_f = _letters_to_f(casc.letter_valuations[li], casc.aps)
        if str(g_f) == "false":
            continue
        tail = _str_f(_And(g_f, _X(tau_f)))
        conjs = _avoid_conjs(pre, tail)
        line1_disjs_f.append(_And(*conjs) if conjs else _tt())
    line1_f = _Or(*line1_disjs_f) if line1_disjs_f else _ff()

    # line (2): stay forever, never blocked (target false never claimed)
    line2_conjs = _avoid_conjs(S, "false")
    line2_f = _And(*line2_conjs) if line2_conjs else _tt()

    res_f = _Or(line1_f, line2_f)
    res = _str_f(res_f)
    _trace(f"    _stay_gt0_weak (wsolid+) res={res[:60]}...")
    return res


def _dashed_change_strong(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade", level: int = 0
) -> str:
    """Formula 5 (dashed / change top), literal per paper p.13 / construction-ref §7:

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
      enumerated over ALL h-image configs (the from-S evaluation was the 2L
      breaker: e.g. for G(a->Xb) no letter from the initial config enters the
      sink's top; entry fires only from the obligation state's lower config).
    - Lines (1)/(2) carry a lower-level prefix reach to T' (cursor level+1);
      δ(⟨T',·⟩,σ) is the observed arrival config of the entering letter
      (reset cascades: independent of the dropped layer state).
    - Line (1) is required separately for Enter(b) = ∅ (line (2) vacuous).
    """
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return reach_strong(S, B, beta, T, tau, casc, level)

    s_val = S[level]
    t_val = T[level]
    b_val = B[level] if B is not None else None
    beta_f = _to_f(beta)
    tau_f = _to_f(tau)

    cls = _combined_letters_at_level(casc, level)

    def _dedupe(triples):
        seen = {}
        for li, pre, arr in triples:
            key = (li, pre[level + 1:])
            if key not in seen:
                seen[key] = (li, pre, arr)
        return list(seen.values())

    # Enter(q): genuine resets to q — witnessed by a pre-config whose layer
    # state differs from q (identity/stay letters never qualify: Enter ⊆ Stay).
    enter_t = _dedupe([(li, pre, arr) for (li, pre, arr) in cls
                       if pre[level] != t_val and arr[level] == t_val])
    enter_b = []
    if B is not None:
        enter_b = _dedupe([(li, pre, arr) for (li, pre, arr) in cls
                           if pre[level] != b_val and arr[level] == b_val])
    leave_s = _dedupe([(li, pre, arr) for (li, pre, arr) in cls
                       if pre[level] == s_val and arr[level] != s_val])

    _trace(f"    _dashed_change_strong level={level}: #enter_t={len(enter_t)} "
           f"#enter_b={len(enter_b)} #leave_s={len(leave_s)}")

    if not enter_t or not leave_s:
        # t never entered, or s never left: a dashed path is impossible.
        return "false"

    entry_disjs_f: List[spot.formula] = []
    for li, pre, arr in enter_t:
        g_f = _letters_to_f(casc.letter_valuations[li], casc.aps)
        if str(g_f) == "false":
            continue
        # inner: after entering t at config arr, solid-stay at t to reach ⟨T,t⟩(τ)
        inner = _solid_stay_strong(arr, B, beta, T, tau, casc, level)
        tail = _str_f(_And(g_f, _X(_to_f(inner))))
        # line (1): freely reach the firing lower config T', then enter + stay
        line_parts_f: List[spot.formula] = [
            _to_f(reach_strong(S, None, "false", pre, tail, casc, level + 1))
        ]
        # line (2): same reach, but parameterized-bad on each potential entry into b:
        # never be about to enter b (η firing) with a weak-stay-at-b that reaches
        # ⟨B,b⟩(β) unreleased by ⟨T,t⟩(τ)  — the SWAPPED wsolid call per the paper.
        for lj, preR, arrR in enter_b:
            eta_f = _letters_to_f(casc.letter_valuations[lj], casc.aps)
            if str(eta_f) == "false":
                continue
            try:
                wsolid_sw = _solid_stay_weak(arrR, T, _str_f(tau_f), B, _str_f(beta_f), casc, level)
            except Exception:
                continue
            bbeta = _str_f(_And(eta_f, _X(_to_f(wsolid_sw))))
            line_parts_f.append(
                _to_f(reach_strong(S, preR, bbeta, pre, tail, casc, level + 1))
            )
        entry_disjs_f.append(_And(*line_parts_f))

    lines12_f = _Or(*entry_disjs_f) if entry_disjs_f else _ff()

    # line (3): the layer state is indeed changed — solid-stay (avoiding bad)
    # up to the moment a Leave letter fires (target = the leave firing point
    # ⟨L,s⟩; does NOT force an immediate change).
    line3_parts_f: List[spot.formula] = []
    for lj, preL, arrL in leave_s:
        lg_f = _letters_to_f(casc.letter_valuations[lj], casc.aps)
        if str(lg_f) == "false":
            continue
        tail_f = lg_f
        if B is not None and preL[level:] == B[level:] and str(beta_f) != "false":
            tail_f = _And(lg_f, _Not(beta_f))
        l3 = _solid_stay_strong(S, B, beta, preL, _str_f(tail_f), casc, level)
        line3_parts_f.append(_to_f(l3))
    line3_f = _Or(*line3_parts_f) if line3_parts_f else _ff()

    return simplify_ltl(_str_f(_And(lines12_f, line3_f)))


# (No weak dashed: the paper has exactly five formulas — weak main (Formula 2)
# is the literal dual of strong main, and Formula 4 (wsolid) is the only other
# weak form. The former bespoke _dashed_change_weak was a non-paper invention
# and was removed when reach_weak became the literal dual.)


# Public API for the operators (reach_strong is primary; weak is its dual or mirror).
# Note: all 1L special case code (one_level_* etc.) has been deleted; only the pure
# generalized inductive implementation remains.
__all__ = [
    "letters_to_prop",
    "make_guard",
    "simplify_ltl",
    "normalize_ltl",
    "reach_strong",
    "reach_weak",
]
