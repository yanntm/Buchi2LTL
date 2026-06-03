"""
reachability_operators.py — Core 1-level (and future inductive) reachability K operators.

Extracted to a smaller module for easier manipulation and to keep the high-level
reconstruct logic in reachability.py small and focused.

These implement the base cases from Boker et al. for reset levels in the cascade.
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


# ---------------------------------------------------------------------------
# Fin(C) sketch per Lemma 7 (uses generalized reach; polish + uncond ↝ / >0 ↝ needed for full)
# ---------------------------------------------------------------------------

def fin_c(C: Tuple[int, ...], casc: "Cascade") -> str:
    """Sketch Fin(C) := ¬(ι ↝ C) ∨ ι ↝ C ( ¬ (C^{>0} ↝ C) ).

    Uses reach_strong for the uncond reach shorthands. Full correct >0 version + init lookup
    and assembly per the paper remain for step 7.
    """
    # robust init
    init: Optional[Tuple[int, ...]] = None
    if casc.original_aut is not None:
        try:
            init = casc.state_to_config.get(casc.original_aut.get_init_state_number())
        except Exception:
            pass
    if init is None:
        cs = casc.all_configs()
        init = cs[0] if cs else C
    # uncond ↝ approx: reach avoiding nothing (beta=false) to C with tau=true, or the "last then never"
    r_to = reach_strong(init, None, "false", C, "true", casc)
    # never-return after last: G( not able to reach C again from C )
    never_again = f"G(!({reach_strong(C, None, 'false', C, 'true', casc)}))"
    return simplify_ltl(f"!({r_to}) | ({r_to} & ({never_again}))")


# ------------------------------------------------------------------
# Small 1-level projection helpers (config tuple <-> scalar pos).
# These are only needed by the 1-level reconstruct logic, but they are
# "operator adjacent" (they turn the Cascade's config automaton into the
# scalar positions the K operators expect). Keeping them here keeps the
# high-level reachability.py (the clean/heuristic policy) smaller and
# more focused.
# ------------------------------------------------------------------

def _config_to_pos(config: Tuple[int, ...]) -> int:
    """For 1-level cascades, the 'position' is the single coordinate (1-based)."""
    if len(config) != 1:
        raise ValueError(f"Expected 1-level config tuple, got {config}")
    return config[0]


def _build_trans_for_pos(casc, pos: int) -> Dict[int, int]:
    """Return {letter_idx: target_pos} for the given pos, using the config automaton."""
    ca = casc.build_configuration_automaton()
    for c, trans_list in ca["transitions"].items():
        if _config_to_pos(c) == pos:
            out: Dict[int, int] = {}
            for li, nc, _val in trans_list:
                out[li] = _config_to_pos(nc)
            return out
    return {}


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
# These recurse on config tuple length (level). Base len==0 or delegated len==1.
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
    n = getattr(casc, "num_levels", 0)
    if level == n:
        b = beta or "false"
        negb = "true" if b == "false" else ("false" if b == "true" else f"!({b})")
        _trace(f"base level reached (level={level}): returning ({negb}) U ({tau})")
        return f"({negb}) U ({tau})"

    _trace(f"reach_strong level={level}/{n} S={S} T={T} beta={beta} tau={tau}")

    if level == 0 and n == 1 and len(S) == 1:
        # Delegate only for pure top-level 1-level cascades (nice output + compat)
        pos_S = _config_to_pos(S)
        pos_T = _config_to_pos(T)
        pos_B = _config_to_pos(B) if B is not None and len(B) == 1 else 0
        trans = _build_trans_for_pos(casc, pos_S)
        return one_level_reach_strong(
            pos_S, pos_B if pos_B else None, pos_T, tau, casc.letter_valuations, casc.aps, trans
        )

    # "0-step from here" only if the *remaining suffix* of the config (from this level onward) already matches target
    suffix_S = S[level:]
    suffix_T = T[level:]
    if suffix_S == suffix_T:
        _trace(f"  suffix from level {level} already matches target -> return tau early")
        return tau

    # Current level's value (for solid/dashed decision at this layer)
    s_val = S[level]
    t_val = T[level]
    b_val = B[level] if B is not None else None
    source_is_target = (suffix_S == suffix_T)  # redundant with above but for clarity in solid
    source_is_bad = (B is not None and s_val == b_val)

    _trace(f"  at level {level}: s_val={s_val} t_val={t_val} source_is_target={source_is_target} source_is_bad={source_is_bad}")

    solid = _solid_stay_strong(S, B, beta, T, tau, casc, level)
    dashed = _dashed_change_strong(S, B, beta, T, tau, casc, level)
    res = f"({solid}) | ({dashed})"
    return simplify_ltl(res)


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

    if level == 0 and n == 1 and len(S) == 1:
        pos_S = _config_to_pos(S)
        pos_T = _config_to_pos(T)
        pos_B = _config_to_pos(B) if B is not None and len(B) == 1 else 0
        trans = _build_trans_for_pos(casc, pos_S)
        return one_level_reach_weak(
            pos_S, pos_B if pos_B else None, pos_T, tau, casc.letter_valuations, casc.aps, trans
        )

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

    _trace(f"  _solid_stay_strong level={level}: source_is_target={source_is_target} source_is_bad={source_is_bad}")

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
            sub_tau = f"({g}) & (X({tau}))"
            sub_beta = f"({g}) & (X({beta}))" if beta not in ("true", "false") else (g if beta == "true" else "false")
            sub_f = reach_strong(arrived, B, sub_beta, T, sub_tau, casc, level + 1)
            term = f"({g}) & (X({sub_f}))"
            _trace(f"      normal sub step -> g & X(sub_f)")
        disjs.append(term)

    or_part = "(" + " | ".join(disjs) + ")" if disjs else "false"
    _trace(f"    or_part at level {level}: {or_part[:80]}...")

    # Conjs ...
    conj: List[str] = [or_part]
    for li, arrived in leave_moves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        sub_tau_l = f"({g}) & (X({tau}))"
        # forbid using full arrived for that leave, at next level
        forbid = reach_strong(arrived, B, "false", T, sub_tau_l, casc, level + 1)
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
            sub_b = f"({g}) & (X({beta}))" if beta not in ("true", "false") else (g if beta == "true" else "false")
            forbid_bad = reach_strong(arrived, B, "false", B, sub_b, casc, level + 1)
            conj.append(f"!(({g}) & (X({forbid_bad})))")

    inner = " & ".join(conj)
    res = f"({inner})" if inner else "false"
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
        sub_tau = f"({g}) & (X({tau}))"
        sub_beta = f"({g}) & (X({beta}))" if beta not in ("true", "false") else (g if beta == "true" else "false")
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
        sub_tau_l = f"({g}) & (X({tau}))"
        forbid = reach_weak(arrived, B, "false", T, sub_tau_l, casc, level + 1)
        conj.append(f"!(({g}) & (X({forbid})))")

    # extra release (simplified)
    for li, arrived in leave_moves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        rel = reach_weak(arrived, B, "false", arrived, "false", casc, level + 1)
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
            sub_b = f"({g}) & (X({beta}))" if beta not in ("true", "false") else (g if beta == "true" else "false")
            forbid_bad = reach_weak(arrived, B, "false", B, sub_b, casc, level + 1)
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
    lower_B = casc.sub_config(B) if B is not None else None

    disjs: List[str] = []
    for li, arrived in enters:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        arrived_lower = casc.sub_config(arrived)
        # tail after entry: once at t, do solid stay at new top (avoiding orig B)
        tail = _solid_stay_strong(arrived, B, beta, T, tau, casc, level)
        entry_tau = f"({g}) & (X({tail}))"
        # (1) entry path, B=S(false) i.e. no special avoid for entry, from S to arrived
        entry1 = reach_strong(S, S, "false", arrived, entry_tau, casc, level)
        # (2) entry while avoiding orig bad, using weak solid for after
        w_tail = _solid_stay_weak(arrived, B, beta, T, tau, casc, level)
        w_entry_tau = f"({g}) & (X({w_tail}))"
        entry2 = reach_weak(S, B, beta, arrived, w_entry_tau, casc, level)
        part12 = f"({entry1}) & ({entry2})"
        # (3) landed cond
        landed_bad = (B is not None and arrived == B)
        cond3 = f"!({beta})" if landed_bad and beta not in ("true", "false") else "true"
        term = f"({part12}) & ({cond3})" if cond3 != "true" else part12
        disjs.append(term)

    or_enters = "(" + " | ".join(disjs) + ")" if disjs else "false"

    # Force actual leave happened (OR over any leave from orig S, with landed-bad cond)
    leaves = casc.compute_stay_leave_from(S).get("leave", [])
    fparts: List[str] = []
    for li, arrived in leaves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        landed_bad = (B is not None and arrived == B)
        c = f"!({beta})" if landed_bad and beta not in ("true", "false") else "true"
        fparts.append(f"({g}) & ({c})" if c != "true" else g)
    if fparts:
        force = "(" + " | ".join(fparts) + ")"
        res = f"({or_enters}) & ({force})"
    else:
        res = or_enters
    return simplify_ltl(res)


def _dashed_change_weak(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade", level: int = 0
) -> str:
    """Weak dual of dashed (stub for now; full mirror would duplicate structure with weak subs)."""
    # For initial impl, fall back to a safe over-approx or the strong negated in dual context.
    # Better: reuse structure but weak.
    # To keep simple and not crash multi, return a G form using current top stay.
    parts = casc.compute_stay_leave_from(S)
    stay = parts.get("stay", [])
    if not stay:
        return "false"
    # crude: G( stay_g | tau ) approx
    gs = []
    for li, _ in stay:
        if li < len(casc.letter_valuations):
            gs.append( letters_to_prop(casc.letter_valuations[li], casc.aps) )
    if not gs:
        return f"G({tau})"
    gdis = "(" + " | ".join(gs) + ")"
    res = f"G( ({gdis}) | ({tau}) )"
    return simplify_ltl(res)


# Re-export the new general API (strong is the primary for reconstruction)
__all__ = [
    "letters_to_prop",
    "make_guard",
    "one_level_reach_stay",
    "one_level_reach_strong",
    "one_level_reach_weak",
    "build_1level_reachability",
    "fin_1level",
    "inf_1level",
    "_config_to_pos",
    "_build_trans_for_pos",
    "simplify_ltl",
    "normalize_ltl",
    "reach_strong",
    "reach_weak",
]
