"""
fin.py — Fin(C) per Lemma 7 of the paper.

Fin(C) := ¬(ι ↝ C) ∨ ι ↝ C ( ¬ (C>0 ↝ C) )

Uses the reachability operators (reachability_operators.py) for the
unconditional shorthands. One-way dependency: the operators never import fin.
The fin counter and its memo live on the CascadeHolder passed as `casc` (per
build), not on the operators module.

Formula objects (spot.formula) in and out — no string round-trips; stringify
only in traces (guarded) or by callers via _str_f/simplify_ltl.
"""

from __future__ import annotations
from typing import Optional, Tuple

from aut2ltl.ltl.builders import _And, _Or, _Not, _X, _ff, _tt, _letters_to_f, _simp_f, _short_f, _fuse_or
import aut2ltl.kr.reachability_operators as _ops
from aut2ltl.kr.reachability_operators import reach_strong, _trace, TRACE_ON


def _uncond_reach_strict(S: Tuple[int, ...], T: Tuple[int, ...], casc: "Cascade") -> "spot.formula":
    """S >0 ↝ T : eventually reach T after at least one strict step (used for C>0 ↝ C in Fin).
    Uses full move + letter guards so that the expansion carries the paper's letter partitions.
    """
    key = (S, T, id(casc))
    if key in casc.uncond_memo:
        return casc.uncond_memo[key]
    if not S:
        res = _ff()
        casc.uncond_memo[key] = res
        return res
    # Letter fusion (dag_folding.md counter-measure B): one disjunct per
    # arrival config, guard = Minato-minimized OR of the letters landing there.
    groups: dict = {}
    for li in range(casc.num_letters()):
        try:
            arrived = casc.move_config(S, li)
        except Exception:
            continue
        g_f = _letters_to_f(casc.letter_valuations[li], casc.aps)
        if g_f.is_ff():
            continue
        key = arrived if _ops._FUSE_LETTERS else (li, arrived)
        groups.setdefault(key, (arrived, []))[1].append(g_f)
    disjs = []
    for arrived, gs in groups.values():
        # after this letter class, from arrived (0-step ok if arrived==T)
        sub = reach_strong(arrived, None, _ff(), T, _tt(), casc)
        disjs.append(_And(_fuse_or(gs), _X(sub)))
    res = _simp_f(_Or(*disjs)) if disjs else _ff()
    casc.uncond_memo[key] = res
    return res


def fin_c(C: Tuple[int, ...], casc: "Cascade") -> "spot.formula":
    """Fin(C) := ¬(ι ↝ C) ∨ ι ↝ C ( ¬ (C>0 ↝ C) ) per Lemma 7 / algorithm.md.

    Uses the reach operators for the uncond shorthands (beta=false, tau=true).
    The >0 version forces progress so that when S==T the "return" requires a move.
    """
    casc.fin_calls += 1
    if casc.fin_calls > 10000:
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
    r_to = reach_strong(init, None, _ff(), C, _tt(), casc)
    if TRACE_ON:
        _trace(f"  fin_c for C={C}: r_to={_short_f(r_to)}")
    # C>0 ↝ C : strict progress return
    r_gt0 = _uncond_reach_strict(C, C, casc)
    if TRACE_ON:
        _trace(f"  fin_c for C={C}: r_gt0={_short_f(r_gt0)}")
    # Paper: second disjunct is the reach parameterized with tau = ¬(C>0 ↝ C)  [plain, not G]
    # so that when claiming at the *last* visit (future possible), the no-return holds at arrival time.
    # The solid/dashed expansion (incl. s==t leave-and-return) allows postponing the claim to future visits.
    no_return_psi = _simp_f(_Not(r_gt0))
    if TRACE_ON:
        _trace(f"  fin_c for C={C}: no_return_psi={_short_f(no_return_psi)}")
    r_with = reach_strong(init, None, _ff(), C, no_return_psi, casc)
    if TRACE_ON:
        _trace(f"  fin_c for C={C}: r_with={_short_f(r_with)}")
    fin_expr = _simp_f(_Or(_Not(r_to), r_with))
    if TRACE_ON:
        _trace(f"  fin_c for C={C}: final={_short_f(fin_expr)}")
    return fin_expr
