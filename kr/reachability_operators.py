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
import functools
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

# Runaway guard on DISTINCT reach subproblems (lru misses, not raw calls).
# Legitimate big builds stay finite — (a U b)|Gc completes at ~285k distinct —
# so the default is generous; an infinite same-level recursion grows without
# bound and still trips it. Wall-clock budgets belong to the callers.
REACH_GUARD = int(os.getenv("KR_REACH_GUARD", "5000000"))

# Simple memo for reach_strong subproblems during one construction.
# Key includes id(casc) for safety. Acts as "unique table of visited" to avoid
# exponential re-expansion of identical (S, B, beta, T, tau, level) subformulas.
# This should prevent the work explosion that looks like "infinite loop".
_reach_memo = {}

# Memo for the five helper formulas (solid/wsolid/dashed and the gt0 cores).
# Only reach_strong was lru-cached; the helpers re-ran their whole
# combined-letter enumeration at every call site (dashed lines (1)/(2)/(3)
# invoke solid/wsolid directly), so the SAME helper signature was recomputed
# under every enclosing context: (a U b)|Gc profiled at 437k raw reach calls
# / 91.5% lru hit rate in 6s — pure fan-in overhead. BDD-style: one entry per
# distinct (helper, casc, S, B, beta, T, tau, level). Cleared with the lru by
# reconstruct and the probes.
_helper_memo: Dict = {}


def _memo_reach_helper(tag: str):
    """Memoize a helper with the (S, B, beta, T, tau, casc, level) signature.
    beta/tau are normalized to hash-consed spot.formula BEFORE keying (str and
    formula spellings of the same guard share an entry). A decorator so the
    function BODY keeps its def-name and code shapes (the r4 audit greps
    bodies by 'def <name>(')."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(S, B, beta, T, tau, casc, level=0):
            beta_f = _ff() if beta is None else _to_f(beta)
            tau_f = _tt() if tau is None else _to_f(tau)
            key = (tag, id(casc), S, B, beta_f, T, tau_f, level)
            hit = _helper_memo.get(key)
            if hit is None:
                hit = fn(S, B, beta_f, T, tau_f, casc, level)
                _helper_memo[key] = hit
            return hit
        return wrapper
    return deco

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
    _tt, _ff, _ap, _And, _Or, _Not, _X, _U,
    _to_f, _letters_to_f, _str_f, _short_f, _simp_f,
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
    beta: "str | spot.formula",
    T: Tuple[int, ...],
    tau: "str | spot.formula",
    casc: "Cascade",
    level: int = 0,
) -> "spot.formula":
    """Formula 1 (main strong): S ~_B(β)^X T(τ) at the given cascade level (coordinate index).

    Recursion advances the level cursor while always passing full-length config tuples
    (so move_config and partition helpers always see correct context for higher coords).
    Base: when level == num_levels, plain (¬β) U τ .

    Native spot.formula end-to-end: accepts beta/tau as str or formula, RETURNS a
    spot.formula (hash-consed → DAG sharing across all subterms; stringify only at
    the very top via reconstruct, or with _str_f in tests/traces).
    Uses lru_cache on _lru_reach_strong (with cid for hashability).
    """
    beta_f = _ff() if beta is None else _to_f(beta)
    tau_f = _tt() if tau is None else _to_f(tau)

    cid = id(casc)
    _register_casc(casc)

    # lru lookup (keyed on hashables: cid + tuples + formula objs; B can be None, which is hashable)
    # (_reach_memo is NOT written here: fin.py uses it with its own 3-tuple
    # keys; the old per-call 7-tuple writes were never read by anyone.)
    return _lru_reach_strong(cid, S, B, beta_f, T, tau_f, level)


@lru_cache(maxsize=None)
def _lru_reach_strong(cid: int, S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta_f: 'spot.formula', T: Tuple[int, ...], tau_f: 'spot.formula', level: int) -> "spot.formula":
    """Core cached implementation of reach_strong. Args are all hashable (B=None ok)."""
    # Dead-tail early-out: reach(S,B,β,T,τ≡false) ≡ false — Table 1 base case
    # is ¬β U false ≡ false and every inductive line conjoins τ at the claim
    # point. With per-node simplify folding tails (σ ∧ X(0) → 0), this deletes
    # the subproblem AND every wrapped descendant it would seed deeper down.
    if tau_f.is_ff():
        return _ff()
    # Guard counts MISSES only (distinct expansions; this body runs once per
    # key). Counting raw calls tripped the guard on healthy 91%-hit workloads.
    global PAPER_REACH_CALLS
    PAPER_REACH_CALLS += 1
    if PAPER_REACH_CALLS > REACH_GUARD:
        raise RuntimeError(
            f"Too many DISTINCT reach_strong subproblems (>{REACH_GUARD}) -- "
            f"genuine blowup (not memo fan-in; hits are not counted). "
            f"KR_REACH_GUARD to tune.")

    casc = _get_casc(cid)
    if casc is None:
        return _ff()

    n = getattr(casc, "num_levels", 0)
    if level == n:
        negb = _tt() if beta_f.is_ff() else _Not(beta_f)
        res_f = _simp_f(_U(negb, tau_f))
        if TRACE_ON:
            _trace(f"base level reached (level={level}): returning {_short_f(res_f)}")
        return res_f

    if TRACE_ON:
        _trace(f"reach_strong level={level}/{n} S={S} T={T} beta={_short_f(beta_f)} tau={_short_f(tau_f)}")

    # 0-step only for trivial tau=true
    suffix_S = S[level:]
    suffix_T = T[level:]
    if suffix_S == suffix_T and tau_f.is_tt():
        _trace(f"  suffix from level {level} already matches target -> return tau early")
        return _tt()

    # Current level's value (for solid/dashed decision at this layer)
    s_val = S[level]
    t_val = T[level]
    b_val = B[level] if B is not None else None
    source_is_target = (suffix_S == suffix_T)
    source_is_bad = (B is not None and s_val == b_val)

    _trace(f"  at level {level}: s_val={s_val} t_val={t_val} source_is_target={source_is_target} source_is_bad={source_is_bad}")

    solid_f = _solid_stay_strong(S, B, beta_f, T, tau_f, casc, level)
    dashed_f = _dashed_change_strong(S, B, beta_f, T, tau_f, casc, level)
    if TRACE_ON:
        _trace(f"    solid={_short_f(solid_f)}")
        _trace(f"    dashed={_short_f(dashed_f)}")

    res_f = _simp_f(_Or(solid_f, dashed_f))
    if TRACE_ON:
        _trace(f"    reach_strong res (pre-memo, post-simp)={_short_f(res_f, 150)}")
    return res_f


def reach_weak(
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
    (The previous bespoke G(τ | ¬β) base was wrong — Table 1 formula 2 at
    level 0 is exactly τ R ¬β — and the bespoke solid_w ∨ dashed_w
    construction was not the paper's Formula 2.)
    """
    if B is None:
        return _tt()
    tau_f = _tt() if tau is None else _to_f(tau)
    beta_f = _ff() if beta is None else _to_f(beta)
    inner = reach_strong(S, T, tau_f, B, beta_f, casc, level)
    return _simp_f(_Not(inner))


@_memo_reach_helper("ss")
def _solid_stay_strong(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: "str | spot.formula", T: Tuple[int, ...], tau: "str | spot.formula", casc: "Cascade", level: int = 0
) -> "spot.formula":
    """Formulas 3 (strong solid/stay top unchanged). Cases on current level's coord.
    Formula objects in and out (str accepted for probe/test compat).
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
        return _ff()

    _trace(f"  _solid_stay_strong level={level}: source_is_target={source_is_target} source_is_bad={source_is_bad}")

    # Immediate collapse for tau=true target (Formula 3: P ∨ true / (P∧¬β) ∨ true)
    if source_is_target and tau_f.is_tt():
        return _tt()

    gt0_f = _stay_gt0_strong(S, B, beta_f, T, tau_f, casc, level)

    if not source_is_bad and not source_is_target:
        return gt0_f
    elif not source_is_bad and source_is_target:
        return _simp_f(_Or(gt0_f, tau_f))
    elif source_is_bad and not source_is_target:
        return _simp_f(_And(gt0_f, _Not(beta_f)))
    else:
        return _simp_f(_Or( _And(gt0_f, _Not(beta_f)) , tau_f ))


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


@_memo_reach_helper("ss0")
def _stay_gt0_strong(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: "str | spot.formula", T: Tuple[int, ...], tau: "str | spot.formula", casc: "Cascade", level: int = 0
) -> "spot.formula":
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
        if g_f.is_ff():
            continue
        tail_f = _simp_f(_And(g_f, _X(tau_f)))
        conj_f: List[spot.formula] = []
        # free reach of the pre-target T' (bad never triggers: beta=false)
        conj_f.append(reach_strong(S, None, _ff(), pre, tail_f, casc, level + 1))
        # Leave-avoid conjuncts
        for lj, preL, arrL in leave_s:
            eta_f = _letters_to_f(casc.letter_valuations[lj], casc.aps)
            if eta_f.is_ff():
                continue
            conj_f.append(reach_strong(S, preL, eta_f, pre, tail_f, casc, level + 1))
        # bad-predecessor conjuncts
        for lk, preB, arrB in bad_pre:
            rho_f = _letters_to_f(casc.letter_valuations[lk], casc.aps)
            if rho_f.is_ff():
                continue
            rb_f = _simp_f(_And(rho_f, _X(beta_f)))
            conj_f.append(reach_strong(S, preB, rb_f, pre, tail_f, casc, level + 1))
        disjs_f.append(_And(*conj_f))

    res_f = _simp_f(_Or(*disjs_f)) if disjs_f else _ff()
    if TRACE_ON:
        _trace(f"    _stay_gt0 result level={level}: {_short_f(res_f, 80)}")
    return res_f


@_memo_reach_helper("ws")
def _solid_stay_weak(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: "str | spot.formula", T: Tuple[int, ...], tau: "str | spot.formula", casc: "Cascade", level: int = 0
) -> "spot.formula":
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
    gt0_f = _stay_gt0_weak(S, B, beta_f, T, tau_f, casc, level)

    if not source_is_bad and not source_is_target:
        return gt0_f
    elif not source_is_bad and source_is_target:
        # Per ref Rws case (S != B and S == T): exactly Rws0 ∨ τ  (gt0 already carries the full weak line1+line2)
        # (Removed special stay_prop U path -- was bypassing gt0/line2 and had dead source_is_bad test inside not-bad branch.)
        return _simp_f(_Or(gt0_f, tau_f))
    elif source_is_bad and not source_is_target:
        return _simp_f(_And(gt0_f, _Not(beta_f)))
    else:
        # Case 4 per corrected paper (weak form): (Rws0 ∨ τ) ∧ ¬β
        return _simp_f(_And( _Or(gt0_f, tau_f) , _Not(beta_f) ))


@_memo_reach_helper("ws0")
def _stay_gt0_weak(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: "str | spot.formula", T: Tuple[int, ...], tau: "str | spot.formula", casc: "Cascade", level: int = 0
) -> "spot.formula":
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

    def _avoid_conjs(target_cfg: Tuple[int, ...], tail_f: "spot.formula") -> List[spot.formula]:
        conjs: List[spot.formula] = []
        for lj, preL, arrL in leave_s:
            eta_f = _letters_to_f(casc.letter_valuations[lj], casc.aps)
            if eta_f.is_ff():
                continue
            conjs.append(reach_weak(S, preL, eta_f, target_cfg, tail_f, casc, level + 1))
        for lk, preB, arrB in bad_pre:
            rho_f = _letters_to_f(casc.letter_valuations[lk], casc.aps)
            if rho_f.is_ff():
                continue
            rb_f = _simp_f(_And(rho_f, _X(beta_f)))
            conjs.append(reach_weak(S, preB, rb_f, target_cfg, tail_f, casc, level + 1))
        return conjs

    # line (1)
    line1_disjs_f: List[spot.formula] = []
    for li, pre, arr in last_steps:
        g_f = _letters_to_f(casc.letter_valuations[li], casc.aps)
        if g_f.is_ff():
            continue
        tail_f = _simp_f(_And(g_f, _X(tau_f)))
        conjs = _avoid_conjs(pre, tail_f)
        line1_disjs_f.append(_And(*conjs) if conjs else _tt())
    line1_f = _Or(*line1_disjs_f) if line1_disjs_f else _ff()

    # line (2): stay forever, never blocked (target false never claimed)
    line2_conjs = _avoid_conjs(S, _ff())
    line2_f = _And(*line2_conjs) if line2_conjs else _tt()

    res_f = _simp_f(_Or(line1_f, line2_f))
    if TRACE_ON:
        _trace(f"    _stay_gt0_weak (wsolid+) res={_short_f(res_f, 60)}")
    return res_f


@_memo_reach_helper("dc")
def _dashed_change_strong(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: "str | spot.formula", T: Tuple[int, ...], tau: "str | spot.formula", casc: "Cascade", level: int = 0
) -> "spot.formula":
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
        return _ff()

    entry_disjs_f: List[spot.formula] = []
    for li, pre, arr in enter_t:
        g_f = _letters_to_f(casc.letter_valuations[li], casc.aps)
        if g_f.is_ff():
            continue
        # inner: after entering t at config arr, solid-stay at t to reach ⟨T,t⟩(τ)
        inner_f = _solid_stay_strong(arr, B, beta_f, T, tau_f, casc, level)
        tail_f = _simp_f(_And(g_f, _X(inner_f)))
        # line (1): freely reach the firing lower config T', then enter + stay
        line_parts_f: List[spot.formula] = [
            reach_strong(S, None, _ff(), pre, tail_f, casc, level + 1)
        ]
        # line (2): same reach, but parameterized-bad on each potential entry into b:
        # never be about to enter b (η firing) with a weak-stay-at-b that reaches
        # ⟨B,b⟩(β) unreleased by ⟨T,t⟩(τ)  — the SWAPPED wsolid call per the paper.
        for lj, preR, arrR in enter_b:
            eta_f = _letters_to_f(casc.letter_valuations[lj], casc.aps)
            if eta_f.is_ff():
                continue
            # Narrow catch: only the "no valid weak form from this entry"
            # shapes. A bare `except Exception` here swallowed EVERYTHING
            # crossing the recursion — including real TypeErrors (heisenbug
            # masked for runs where this path enclosed it) and test-harness
            # control exceptions (probe budget alarms silently ignored).
            try:
                wsolid_sw = _solid_stay_weak(arrR, T, tau_f, B, beta_f, casc, level)
            except (ValueError, IndexError, KeyError):
                continue
            bbeta_f = _simp_f(_And(eta_f, _X(wsolid_sw)))
            line_parts_f.append(
                reach_strong(S, preR, bbeta_f, pre, tail_f, casc, level + 1)
            )
        entry_disjs_f.append(_And(*line_parts_f))

    lines12_f = _Or(*entry_disjs_f) if entry_disjs_f else _ff()

    # line (3): the layer state is indeed changed — solid-stay (avoiding bad)
    # up to the moment a Leave letter fires (target = the leave firing point
    # ⟨L,s⟩; does NOT force an immediate change).
    line3_parts_f: List[spot.formula] = []
    for lj, preL, arrL in leave_s:
        lg_f = _letters_to_f(casc.letter_valuations[lj], casc.aps)
        if lg_f.is_ff():
            continue
        tail_f = lg_f
        if B is not None and preL[level:] == B[level:] and not beta_f.is_ff():
            tail_f = _And(lg_f, _Not(beta_f))
        line3_parts_f.append(_solid_stay_strong(S, B, beta_f, preL, tail_f, casc, level))
    line3_f = _Or(*line3_parts_f) if line3_parts_f else _ff()

    return _simp_f(_And(lines12_f, line3_f))


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
