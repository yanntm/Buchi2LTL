"""
reachability_operators.py — Reachability operators for the Krohn-Rhodes cascade LTL construction.

Implements the 5 inductive reachability formulas (strong/weak, solid-stay/dashed-change,
with >0 variants) from Boker et al. (paper Sec 4.2 / algorithm.md Table 1),
guard helpers, and fin_c (Lemma 7). All 1L special case code has been deleted;
the path is the pure paper inductive for all cascade depths.

The high-level assembly using these (plus Fin + Muller DNF) lives in reachability.py.
All driven uniformly by Cascade config transitions and letter valuations (no patterns
on the automaton shape; the normalized det aut in the Cascade *is* the working D).
"""

from __future__ import annotations
from typing import Callable, Dict, List, Optional, Tuple
import os

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

def _trace(msg: str) -> None:
    if TRACE_ON:
        print("[KR] " + msg)

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


# Level-1 (1L cascade) special case code has been deleted entirely per requirements.
# The implementation uses only the uniform generalized inductive 5 formulas + base
# (level == num_levels -> Until) for all depths. No delegation or scalar 1L helpers in the main path.




# ---------------------------------------------------------------------------
# Fin(C) per Lemma 7 (implemented in fin_c using generalized reach; the 1L-only
# fin_1level/inf_1level placeholders were removed as non-general and unused).
# ---------------------------------------------------------------------------

def _uncond_reach_strict(S: Tuple[int, ...], T: Tuple[int, ...], casc: "Cascade") -> str:
    """S >0 ↝ T : eventually reach T after at least one strict step (used for C>0 ↝ C in Fin).
    Uses full move + letter guards so that the expansion carries the paper's letter partitions.
    """
    key = (S, T, id(casc))
    if key in _reach_memo:
        return _reach_memo[key]
    if not S:
        res = "false"
        _reach_memo[key] = res
        return res
    disjs = []
    for li in range(casc.num_letters()):
        try:
            arrived = casc.move_config(S, li)
            g = letters_to_prop(casc.letter_valuations[li], casc.aps)
            if g in ("false", "0"):
                continue
            # after this letter, from arrived (0-step ok if arrived==T)
            sub = reach_strong(arrived, None, "false", T, "true", casc)
            disjs.append(f"({g}) & (X({sub}))")
        except Exception:
            continue
    if not disjs:
        res = "false"
    else:
        res = simplify_ltl(" | ".join( f"({d})" for d in disjs ))
    _reach_memo[key] = res
    return res


def fin_c(C: Tuple[int, ...], casc: "Cascade") -> str:
    """Fin(C) := ¬(ι ↝ C) ∨ ι ↝ C ( ¬ (C>0 ↝ C) ) per Lemma 7 / algorithm.md.

    Uses the reach operators for the uncond shorthands (beta=false, tau=true).
    The >0 version forces progress so that when S==T the "return" requires a move.
    """
    global PAPER_FIN_CALLS
    PAPER_FIN_CALLS += 1
    if PAPER_FIN_CALLS > 10000:
        raise RuntimeError("Too many fin_c calls -- repeated Fin on same C exploding the construction")
    # robust init (from the normalized det D stored in the Cascade; this D is
    # the authoritative input to the algorithm)
    init: Optional[Tuple[int, ...]] = None
    if casc.original_aut is not None:
        try:
            init = casc.state_to_config.get(casc.original_aut.get_init_state_number())
        except Exception:
            pass
    if init is None:
        cs = casc.all_configs()
        init = cs[0] if cs else C
    # ι ↝ C (can be 0-step if init==C)
    r_to = simplify_ltl(reach_strong(init, None, "false", C, "true", casc))
    _trace(f"  fin_c for C={C}: r_to={r_to}")
    # C>0 ↝ C : strict progress return
    r_gt0 = simplify_ltl(_uncond_reach_strict(C, C, casc))
    _trace(f"  fin_c for C={C}: r_gt0={r_gt0}")
    # Paper: second disjunct is the reach parameterized with tau = ¬(C>0 ↝ C)  [plain, not G]
    # so that when claiming at the *last* visit (future possible), the no-return holds at arrival time.
    # The U/gt0 expansion in solid (when S==C) allows postponing the claim to future visits.
    no_return_psi = simplify_ltl(f"!({r_gt0})")
    _trace(f"  fin_c for C={C}: no_return_psi={no_return_psi}")
    r_with = simplify_ltl(reach_strong(init, None, "false", C, no_return_psi, casc))
    _trace(f"  fin_c for C={C}: r_with={r_with}")
    fin_expr = simplify_ltl(f"!({r_to}) | ({r_with})")
    _trace(f"  fin_c for C={C}: final={fin_expr}")
    return fin_expr


# 1-level projection helpers deleted entirely (were only for the removed 1L special case code).


# ---------------------------------------------------------------------------
# Guard / LTL simplification (cross-cutting, step 5 in roadmap)
# ---------------------------------------------------------------------------

def simplify_ltl(expr: str) -> str:
    """Simplify an LTL formula string using Spot (if available). Reduces DNF size from
    full letter disjunctions etc. Purely algebraic on the produced expr; no aut shape used.
    """
    if not expr or expr in ("true", "false"):
        return expr
    try:
        import spot
        f = spot.formula(expr)
        fs = f.simplify()
        s = str(fs)
        return _normalize_ltl(s)
    except Exception:
        return _normalize_ltl(expr)  # keep as-is if cannot simplify


def _normalize_ltl(s: str) -> str:
    """Spot often uses 1/0 for true/false (parses words but outputs 0/1 in many cases).
    Normalize for consistent I/O and tests.
    """
    if s in ("1", "true"):
        return "true"
    if s in ("0", "false"):
        return "false"
    return s


def normalize_ltl(expr: str) -> str:
    """Normalize + simplify (Spot 0/1 -> true/false words for nicer output and test I/O)."""
    return simplify_ltl(expr)


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
    """
    # Instrumentation (per user): count to detect explosion / infinite recursion
    # (no caching yet; repeated identical subproblems on same (S,T,level) can cause blowup).
    global PAPER_REACH_CALLS
    PAPER_REACH_CALLS += 1
    if PAPER_REACH_CALLS > 100000:
        raise RuntimeError("Too many reach_strong calls (>100k) -- likely explosion from lack of memoization on sub-reach or infinite rec on same-level moves")
    # Normalize beta/tau *early* using simplify. This prevents the formula strings from
    # growing "infinitely" (exponentially nested) when composing in >0, leave conjs, dashed,
    # and especially when used inside Fin's G(!reach) and the DNF assembly.
    # Many composed "(!a & X(true))" etc collapse, and equivalent subproblems share via memo.
    beta = simplify_ltl(beta or "false")
    tau = simplify_ltl(tau or "true")
    # Memo lookup (unique table) using *normalized* beta/tau so sharing works across compositions.
    key = (S, B if B is not None else (), beta, T, tau, level, id(casc))
    if key in _reach_memo:
        return _reach_memo[key]
    n = getattr(casc, "num_levels", 0)
    if level == n:
        b = beta or "false"
        negb = "true" if b == "false" else ("false" if b == "true" else f"!({b})")
        _trace(f"base level reached (level={level}): returning ({negb}) U ({tau})")
        res = f"({negb}) U ({tau})"
        _reach_memo[key] = res
        return res

    _trace(f"reach_strong level={level}/{n} S={S} T={T} beta={beta} tau={tau}")

    # "0-step from here" only if the *remaining suffix* of the config (from this level onward)
    # already matches the target *and* the pending tau is the trivial success "true".
    # For complex tau (e.g. a last-visit psi like "a" or G expr in Fin(C) construction),
    # even if at target config we must expand via solid (gt0 | tau or U form) to allow
    # additional self-steps / future visits to C before claiming the tau at a later visit.
    # This is required for correct Fin on transient start states (to produce Fa not "a"/Ga).
    suffix_S = S[level:]
    suffix_T = T[level:]
    if suffix_S == suffix_T and tau == "true":
        _trace(f"  suffix from level {level} already matches target -> return tau early")
        _reach_memo[key] = "true"
        return "true"

    # Current level's value (for solid/dashed decision at this layer)
    s_val = S[level]
    t_val = T[level]
    b_val = B[level] if B is not None else None
    source_is_target = (suffix_S == suffix_T)  # redundant with above but for clarity in solid
    source_is_bad = (B is not None and s_val == b_val)

    _trace(f"  at level {level}: s_val={s_val} t_val={t_val} source_is_target={source_is_target} source_is_bad={source_is_bad}")

    solid = _solid_stay_strong(S, B, beta, T, tau, casc, level)
    dashed = _dashed_change_strong(S, B, beta, T, tau, casc, level)
    _trace(f"    solid={solid[:120]}{'...' if len(solid)>120 else ''}")
    _trace(f"    dashed={dashed[:120]}{'...' if len(dashed)>120 else ''}")
    res = f"({solid}) | ({dashed})"
    res = simplify_ltl(res)
    _trace(f"    reach_strong res (pre-memo, post-simp)={res[:150]}{'...' if len(res)>150 else ''}")
    _reach_memo[key] = res
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
    """Formula 2 (weak dual of main)."""
    n = getattr(casc, "num_levels", 0)
    if level == n:
        return f"G( ({tau}) | !({beta or 'false'}) )"

    solid_w = _solid_stay_weak(S, B, beta, T, tau, casc, level)
    dashed_w = _dashed_change_weak(S, B, beta, T, tau, casc, level)
    res = f"({solid_w}) | ({dashed_w})"
    return simplify_ltl(res)


def _solid_stay_strong(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade", level: int = 0
) -> str:
    """Formulas 3 (strong solid/stay top unchanged). Cases on current level's coord."""
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return reach_strong(S, B, beta, T, tau, casc, level)

    s_val = S[level]
    t_val = T[level]
    b_val = B[level] if B is not None else None
    source_is_bad = (B is not None and s_val == b_val)
    suffix_S = S[level:]
    suffix_T = T[level:]
    source_is_target = (suffix_S == suffix_T)

    if s_val != t_val:
        # Solid-stay (Formulas 3/4) requires the top-level component at this layer to remain s throughout.
        # If T requires a different top at this layer, solid is impossible; dashed (change) must be used.
        _trace(f"  _solid_stay_strong level={level}: s_val({s_val}) != t_val({t_val}) -> solid impossible, return false")
        return "false"

    _trace(f"  _solid_stay_strong level={level}: source_is_target={source_is_target} source_is_bad={source_is_bad}")

    # Immediate collapse per paper Formula 3: when source suffix matches target at this layer and
    # the attached tau is (simplified to) true, the (gt0 | tau) or equiv is true; avoid expanding
    # gt0 (which would build unnecessary nesting of X-chains for self-stay even when | true collapses).
    if source_is_target and tau == "true":
        if source_is_bad:
            # (gt0 & !beta) | true -> true regardless
            return "true"
        return "true"

    # For source==target (solid), use U form over stay_gs when there are stays: this supports
    # claiming the (possibly complex) tau after arbitrary future visits to self. Needed for
    # Fin(C) last-visit semantics on start states (produces e.g. Fa for transient init instead
    # of shallow "a"). Degenerates when no stay. The stay_g already restricts to allowed stay
    # letters (conjs for leaves are implicit as U phi only permits stay props before psi).
    if source_is_target:
        stay_moves = casc.compute_stay_leave_from(S).get("stay", [])
        stay_props = []
        for li, _ in stay_moves:
            if li < len(casc.letter_valuations):
                gg = letters_to_prop(casc.letter_valuations[li], casc.aps)
                if gg not in ("false", "0", ""):
                    stay_props.append(gg)
        if stay_props:
            sg = stay_props[0] if len(stay_props) == 1 else "(" + " | ".join(stay_props) + ")"
            sg = simplify_ltl(sg)
            if sg != "false":
                uform = simplify_ltl(f"({sg}) U ({tau})")
                if source_is_bad:
                    uform = simplify_ltl(f"({uform}) & !({beta})")
                elif beta not in ("false", "true"):
                    # for safety under bad? paper cases vary; keep simple for target not-bad
                    pass
                return uform
        # fallthrough if no stays: gt0 will be false-ish, | tau will give tau

    gt0 = _stay_gt0_strong(S, B, beta, T, tau, casc, level)

    if not source_is_bad and not source_is_target:
        return gt0
    elif not source_is_bad and source_is_target:
        return simplify_ltl(f"({gt0}) | ({tau})")
    elif source_is_bad and not source_is_target:
        return simplify_ltl(f"({gt0}) & !({beta})")
    else:
        return simplify_ltl(f"(({gt0}) & !({beta})) | ({tau})")


def _stay_gt0_strong(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade", level: int = 0
) -> str:
    """The >0 common subformula for solid strong at `level`.
    We always use *full* config tuples for move/partition so context of higher levels is preserved.
    Sub-recursive calls advance `level` and pass the *full arrived config*.
    """
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return reach_strong(S, B, beta, T, tau, casc, level)

    parts = casc.compute_stay_leave_from(S)  # full S always
    stay_moves = parts.get("stay", [])
    leave_moves = parts.get("leave", [])

    _trace(f"    _stay_gt0_strong level={level}: #stay={len(stay_moves)} #leave={len(leave_moves)}")

    # OR over stay moves at this level: g & X ( sub_reach at level+1 from *full arrived* )
    disjs: List[str] = []
    for li, arrived in stay_moves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        # If this letter lands the *remaining* suffix (from next level) exactly on target,
        # then we have arrived at overall target with this step; attach outer tau after the X, no extra sub g.
        arrived_suffix = arrived[level+1:]
        target_suffix = T[level+1:]
        if arrived_suffix == target_suffix:
            term = f"({g}) & (X({tau}))"
            _trace(f"      landing completes target at this step -> g & X(tau)  (g={g})")
        else:
            sub_tau = simplify_ltl(f"({g}) & (X({tau}))")
            sub_beta = simplify_ltl(f"({g}) & (X({beta}))") if beta not in ("true", "false") else (g if beta == "true" else "false")
            sub_f = reach_strong(arrived, B, sub_beta, T, sub_tau, casc, level + 1)
            term = f"({g}) & (X({sub_f}))"
            _trace(f"      normal sub step -> g & X(sub_f)")
        disjs.append(term)

    or_part = "(" + " | ".join(disjs) + ")" if disjs else "false"
    or_part = simplify_ltl(or_part)
    _trace(f"    or_part at level {level}: {or_part[:80]}...")

    # Conjs ...
    conj: List[str] = [or_part]
    for li, arrived in leave_moves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        sub_tau_l = simplify_ltl(f"({g}) & (X({tau}))")
        # forbid using full arrived for that leave, at next level
        forbid = reach_strong(arrived, B, "false", T, sub_tau_l, casc, level + 1)
        forbid = simplify_ltl(forbid)
        conj.append(f"!(({g}) & (X({forbid})))")

    # bad landing conjs (using full)
    if B is not None:
        for li, arrived in stay_moves:
            if li >= len(casc.letter_valuations):
                continue
            if arrived != B:  # landed exactly on the bad full config at this step
                continue
            g = letters_to_prop(casc.letter_valuations[li], casc.aps)
            if g == "false":
                continue
            sub_b = simplify_ltl(f"({g}) & (X({beta}))") if beta not in ("true", "false") else (g if beta == "true" else "false")
            forbid_bad = reach_strong(arrived, B, "false", B, sub_b, casc, level + 1)
            forbid_bad = simplify_ltl(forbid_bad)
            conj.append(f"!(({g}) & (X({forbid_bad})))")

    inner = " & ".join(conj)
    res = simplify_ltl( f"({inner})" if inner else "false" )
    _trace(f"    _stay_gt0 conj parts: {conj}")
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
    source_is_bad = (B is not None and s_val == b_val)
    source_is_target = (s_val == t_val)

    if s_val != t_val:
        _trace(f"  _solid_stay_weak level={level}: s_val({s_val}) != t_val({t_val}) -> solid impossible, return false")
        return "false"

    gt0 = _stay_gt0_weak(S, B, beta, T, tau, casc, level)

    if not source_is_bad and not source_is_target:
        return gt0
    elif not source_is_bad and source_is_target:
        return simplify_ltl(f"({gt0}) | ({tau})")
    elif source_is_bad and not source_is_target:
        return simplify_ltl(f"({gt0}) & !({beta})")
    else:
        # weak allows the τ even under bad in some
        return simplify_ltl(f"({gt0}) | ({tau}) & !({beta})")


def _stay_gt0_weak(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade", level: int = 0
) -> str:
    """ >0 weak for solid. Similar structure, weak subcalls, extra release conjs for leaves."""
    n = getattr(casc, "num_levels", 0)
    if level >= n:
        return reach_weak(S, B, beta, T, tau, casc, level)

    parts = casc.compute_stay_leave_from(S)
    stay_moves = parts.get("stay", [])
    leave_moves = parts.get("leave", [])

    disjs: List[str] = []
    for li, arrived in stay_moves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        sub_tau = simplify_ltl(f"({g}) & (X({tau}))")
        sub_beta = simplify_ltl(f"({g}) & (X({beta}))") if beta not in ("true", "false") else (g if beta == "true" else "false")
        sub_f = reach_weak(arrived, B, sub_beta, T, sub_tau, casc, level + 1)
        disjs.append(f"({g}) & (X({sub_f}))")

    or_part = "(" + " | ".join(disjs) + ")" if disjs else "false"

    conj: List[str] = [or_part]
    for li, arrived in leave_moves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        sub_tau_l = simplify_ltl(f"({g}) & (X({tau}))")
        forbid = reach_weak(arrived, B, "false", T, sub_tau_l, casc, level + 1)
        forbid = simplify_ltl(forbid)
        conj.append(f"!(({g}) & (X({forbid})))")

    # extra release (simplified)
    for li, arrived in leave_moves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        rel = reach_weak(arrived, B, "false", arrived, "false", casc, level + 1)
        rel = simplify_ltl(rel)
        conj.append(f"(({g}) => (X({rel})))")

    if B is not None:
        for li, arrived in stay_moves:
            if li >= len(casc.letter_valuations):
                continue
            if arrived != B:
                continue
            g = letters_to_prop(casc.letter_valuations[li], casc.aps)
            if g == "false":
                continue
            sub_b = simplify_ltl(f"({g}) & (X({beta}))") if beta not in ("true", "false") else (g if beta == "true" else "false")
            forbid_bad = reach_weak(arrived, B, "false", B, sub_b, casc, level + 1)
            forbid_bad = simplify_ltl(forbid_bad)
            conj.append(f"!(({g}) & (X({forbid_bad})))")

    inner = " & ".join(conj)
    return f"({inner})" if inner else "false"


def _dashed_change_strong(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade", level: int = 0
) -> str:
    """Formula 5 (dashed / change top, most complex)."""
    s_top = casc.top_of(S)
    t_top = casc.top_of(T)
    if s_top == t_top:
        return "false"

    enters = casc.compute_enters_to_from(S, t_top)
    if not enters:
        return "false"

    lower_T = casc.sub_config(T)

    disjs: List[str] = []
    for li, arrived in enters:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        # tail after entry: once at t, do solid stay at new top (avoiding orig B)
        tail = _solid_stay_strong(arrived, B, beta, T, tau, casc, level)
        core = f"({g}) & (X({tail}))"
        # When lower suffix of target is empty (this layer change sets the final coordinate),
        # the enter term can use the base U form (not beta U core) for the <>~<> (psi) attachment
        # matching the paper's level-0 until when the sub-config is exhausted.
        if not lower_T:
            b = beta or "false"
            negb = "true" if b == "false" else ("false" if b == "true" else f"!({b})")
            core = f"({negb}) U ({core})"
        # (3) landed cond (common)
        landed_bad = (B is not None and arrived == B)
        cond3 = f"!({beta})" if landed_bad and beta not in ("true", "false") else "true"
        if cond3 != "true":
            core = f"({core}) & ({cond3})"
        disjs.append(simplify_ltl(core))

    or_enters = "(" + " | ".join(disjs) + ")" if disjs else "false"
    or_enters = simplify_ltl(or_enters)

    # Note: no outer & force on leaves here (would force immediate change on first letter).
    # When lower_T empty the enter cores above injected (notb U core) providing the base
    # <>~<> (psi) for 1L change cases (giving F for Fa). For multiL eventual at layer
    # may be provided by recursion / outer solid gt0 landing or keys.
    return or_enters


def _dashed_change_weak(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade", level: int = 0
) -> str:
    """Weak (Formula 4/2) version for dashed change top (solid-stay weak + release)."""
    # Mirrors the structure of the strong dashed but uses weak sub-reach for the
    # prefix/avoidance to ensure the overall formula stays in the appropriate
    # safety class per the paper. Uses stay/leave partitions from the cascade.
    parts = casc.compute_stay_leave_from(S)
    stay = parts.get("stay", [])
    if not stay:
        return "false"
    gs = []
    for li, _ in stay:
        if li < len(casc.letter_valuations):
            gs.append( letters_to_prop(casc.letter_valuations[li], casc.aps) )
    if not gs:
        return f"G({tau})"
    gdis = "(" + " | ".join(gs) + ")"
    res = f"G( ({gdis}) | ({tau}) )"
    return simplify_ltl(res)


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
