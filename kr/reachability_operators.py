"""
reachability_operators.py — Core 1-level (and future inductive) reachability K operators.

Extracted to a smaller module for easier manipulation and to keep the high-level
reconstruct logic in reachability.py small and focused.

These implement the base cases from Boker et al. for reset levels in the cascade.
"""

from __future__ import annotations
from typing import Callable, Dict, List, Optional, Tuple

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
) -> str:
    """Formula 1 (main strong): S ~_B(β)^X T(τ).

    - level 0 (empty configs): (¬β) U τ
    - len==1: delegate to specialized one_level_reach_strong (optimized base case, no extra X)
    - higher: solid-stay or dashed-change (or-ed; one will be false if tops mismatch)
    """
    if len(S) == 0 and len(T) == 0:
        b = beta or "false"
        negb = "true" if b == "false" else ("false" if b == "true" else f"!({b})")
        return f"({negb}) U ({tau})"

    if len(S) == 1 and getattr(casc, "num_levels", 0) == 1:
        # Delegate to 1-level base ONLY when this is the top-level of a 1-level cascade
        # (preserves nice output without extra X nesting + full compat for existing 1-level cases).
        pos_S = _config_to_pos(S)
        pos_T = _config_to_pos(T)
        pos_B = _config_to_pos(B) if B is not None and len(B) == 1 else 0
        trans = _build_trans_for_pos(casc, pos_S)
        return one_level_reach_strong(
            pos_S, pos_B if pos_B else None, pos_T, tau, casc.letter_valuations, casc.aps, trans
        )

    # All other cases (multi-level top or recursive sub-levels): use inductive solid/dashed
    # (for sub len==1 this bottoms out using level-0 base U with X-adjusted guards)
    solid = _solid_stay_strong(S, B, beta, T, tau, casc)
    dashed = _dashed_change_strong(S, B, beta, T, tau, casc)
    res = f"({solid}) | ({dashed})"
    return simplify_ltl(res)


def reach_weak(
    S: Tuple[int, ...],
    B: Optional[Tuple[int, ...]],
    beta: str,
    T: Tuple[int, ...],
    tau: str,
    casc: "Cascade",
) -> str:
    """Formula 2 (weak dual of main)."""
    if len(S) == 0 and len(T) == 0:
        # dual approx for base
        return f"G( ({tau}) | !({beta or 'false'}) )"

    if len(S) == 1 and getattr(casc, "num_levels", 0) == 1:
        pos_S = _config_to_pos(S)
        pos_T = _config_to_pos(T)
        pos_B = _config_to_pos(B) if B is not None and len(B) == 1 else 0
        trans = _build_trans_for_pos(casc, pos_S)
        return one_level_reach_weak(
            pos_S, pos_B if pos_B else None, pos_T, tau, casc.letter_valuations, casc.aps, trans
        )

    solid_w = _solid_stay_weak(S, B, beta, T, tau, casc)
    dashed_w = _dashed_change_weak(S, B, beta, T, tau, casc)
    res = f"({solid_w}) | ({dashed_w})"
    return simplify_ltl(res)


def _solid_stay_strong(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade"
) -> str:
    """Formulas 3 (strong solid/stay top unchanged). Cases on S==B, S==T at this level."""
    if len(S) == 0:
        return reach_strong(S, B, beta, T, tau, casc)

    s_top = casc.top_of(S)
    t_top = casc.top_of(T)
    if s_top != t_top:
        return "false"  # cannot stay to different top

    b_top = casc.top_of(B) if B is not None else None
    source_is_bad = (B is not None and S == B)
    source_is_target = (S == T)

    gt0 = _stay_gt0_strong(S, B, beta, T, tau, casc)

    if not source_is_bad and not source_is_target:
        return gt0
    elif not source_is_bad and source_is_target:
        return simplify_ltl(f"({gt0}) | ({tau})")
    elif source_is_bad and not source_is_target:
        return simplify_ltl(f"({gt0}) & !({beta})")
    else:
        return simplify_ltl(f"(({gt0}) & !({beta})) | ({tau})")


def _stay_gt0_strong(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade"
) -> str:
    """The >0 common subformula for solid strong: disj over stay steps (first letter keep top) + sub reach from *arrived*,
    conjoined with negations over leave steps and bad-landing steps.
    """
    if len(S) == 0:
        return reach_strong(S, B, beta, T, tau, casc)

    parts = casc.compute_stay_leave_from(S)
    stay_moves = parts.get("stay", [])
    leave_moves = parts.get("leave", [])

    lower_T = casc.sub_config(T)
    lower_B = casc.sub_config(B) if B is not None else None
    lower_S0 = casc.sub_config(S)

    # OR over stay moves: g & X ( lower_reach from *arrived_lower* to lower_T with adjusted )
    disjs: List[str] = []
    for li, arrived in stay_moves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        arrived_lower = casc.sub_config(arrived)
        sub_tau = f"({g}) & (X({tau}))"
        sub_beta = f"({g}) & (X({beta}))" if beta not in ("true", "false") else (g if beta == "true" else "false")
        # recurse lower (will delegate at bottom)
        sub_f = reach_strong(arrived_lower, lower_B, sub_beta, lower_T, sub_tau, casc)
        disjs.append(f"({g}) & (X({sub_f}))")

    or_part = "(" + " | ".join(disjs) + ")" if disjs else "false"

    # Conjs to enforce stay + avoid bad: negate leave paths that "reach target anyway", and bad landings under beta
    conj: List[str] = [or_part]
    # 1. leaves: cannot leave and then lower-reach the target (would violate stay-top)
    for li, arrived in leave_moves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        arrived_lower = casc.sub_config(arrived)
        sub_tau_l = f"({g}) & (X({tau}))"
        # from arrived after leave, could I reach the lower target (beta=false for this check)
        forbid = reach_strong(arrived_lower, None, "false", lower_T, sub_tau_l, casc)
        conj.append(f"!(({g}) & (X({forbid})))")

    # 2. bad landings under stay letters (if land on bad lower+same top, then suffix must not satisfy beta)
    if B is not None:
        bad_lower = casc.sub_config(B)
        for li, arrived in stay_moves:
            if li >= len(casc.letter_valuations):
                continue
            if casc.sub_config(arrived) != bad_lower:
                continue
            g = letters_to_prop(casc.letter_valuations[li], casc.aps)
            if g == "false":
                continue
            arrived_l = casc.sub_config(arrived)
            sub_b = f"({g}) & (X({beta}))" if beta not in ("true", "false") else (g if beta == "true" else "false")
            # negate (take step to bad & X (satisfy beta or reach-from-bad under it))
            forbid_bad = reach_strong(arrived_l, None, "false", bad_lower, sub_b, casc)
            conj.append(f"!(({g}) & (X({forbid_bad})))")

    inner = " & ".join(conj)
    return f"({inner})" if inner else "false"


def _solid_stay_weak(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade"
) -> str:
    """Formula 4 (weak solid/stay). Mirror of strong but uses weak subs + slightly different case ors."""
    if len(S) == 0:
        return reach_weak(S, B, beta, T, tau, casc)

    s_top = casc.top_of(S)
    t_top = casc.top_of(T)
    if s_top != t_top:
        return "false"

    source_is_bad = (B is not None and S == B)
    source_is_target = (S == T)

    gt0 = _stay_gt0_weak(S, B, beta, T, tau, casc)

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
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade"
) -> str:
    """ >0 weak for solid. Similar structure, weak subcalls, extra release conjs for leaves (S~S(false))."""
    if len(S) == 0:
        return reach_weak(S, B, beta, T, tau, casc)

    parts = casc.compute_stay_leave_from(S)
    stay_moves = parts.get("stay", [])
    leave_moves = parts.get("leave", [])

    lower_T = casc.sub_config(T)
    lower_B = casc.sub_config(B) if B is not None else None

    disjs: List[str] = []
    for li, arrived in stay_moves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        arrived_lower = casc.sub_config(arrived)
        sub_tau = f"({g}) & (X({tau}))"
        sub_beta = f"({g}) & (X({beta}))" if beta not in ("true", "false") else (g if beta == "true" else "false")
        sub_f = reach_weak(arrived_lower, lower_B, sub_beta, lower_T, sub_tau, casc)
        disjs.append(f"({g}) & (X({sub_f}))")

    or_part = "(" + " | ".join(disjs) + ")" if disjs else "false"

    conj: List[str] = [or_part]
    for li, arrived in leave_moves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        arrived_lower = casc.sub_config(arrived)
        sub_tau_l = f"({g}) & (X({tau}))"
        forbid = reach_weak(arrived_lower, None, "false", lower_T, sub_tau_l, casc)
        conj.append(f"!(({g}) & (X({forbid})))")

    # extra release conjs for weak (S~S(false) under leave, to cover "not yet target" release)
    for li, arrived in leave_moves:
        if li >= len(casc.letter_valuations):
            continue
        g = letters_to_prop(casc.letter_valuations[li], casc.aps)
        if g == "false":
            continue
        arrived_lower = casc.sub_config(arrived)
        # weak reach to "self" (arrived) with false target (release not leaving? or not hitting)
        rel = reach_weak(arrived_lower, lower_B, "false", arrived_lower, "false", casc)
        conj.append(f"(({g}) => (X({rel})))")  # or just include in ands; use => or G form

    if B is not None:
        bad_lower = casc.sub_config(B)
        for li, arrived in stay_moves:
            if casc.sub_config(arrived) != bad_lower:
                continue
            if li >= len(casc.letter_valuations):
                continue
            g = letters_to_prop(casc.letter_valuations[li], casc.aps)
            if g == "false":
                continue
            arrived_l = casc.sub_config(arrived)
            sub_b = f"({g}) & (X({beta}))" if beta not in ("true", "false") else (g if beta == "true" else "false")
            forbid_bad = reach_weak(arrived_l, None, "false", bad_lower, sub_b, casc)
            conj.append(f"!(({g}) & (X({forbid_bad})))")

    inner = " & ".join(conj)
    return f"({inner})" if inner else "false"


def _dashed_change_strong(
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade"
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
        tail = _solid_stay_strong(arrived, B, beta, T, tau, casc)
        entry_tau = f"({g}) & (X({tail}))"
        # (1) entry path, B=S(false) i.e. no special avoid for entry, from S to arrived
        entry1 = reach_strong(S, S, "false", arrived, entry_tau, casc)
        # (2) entry while avoiding orig bad, using weak solid for after
        w_tail = _solid_stay_weak(arrived, B, beta, T, tau, casc)
        w_entry_tau = f"({g}) & (X({w_tail}))"
        entry2 = reach_weak(S, B, beta, arrived, w_entry_tau, casc)
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
    S: Tuple[int, ...], B: Optional[Tuple[int, ...]], beta: str, T: Tuple[int, ...], tau: str, casc: "Cascade"
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
