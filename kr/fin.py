"""
fin.py — Fin(C) per Lemma 7 of the paper.

Fin(C) := ¬(ι ↝ C) ∨ ι ↝ C ( ¬ (C>0 ↝ C) )

Uses the reachability operators (reachability_operators.py) for the
unconditional shorthands. One-way dependency: the operators never import fin.
Counters and the shared memo live on the operators module (mutated via module
attribute so resets by callers keep working).
"""

from __future__ import annotations
from typing import Optional, Tuple

from kr.ltl_builders import letters_to_prop, simplify_ltl
import kr.reachability_operators as _ops
from kr.reachability_operators import reach_strong, _reach_memo, _trace


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
    _ops.PAPER_FIN_CALLS += 1
    if _ops.PAPER_FIN_CALLS > 10000:
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
    # The solid/dashed expansion (incl. s==t leave-and-return) allows postponing the claim to future visits.
    no_return_psi = simplify_ltl(f"!({r_gt0})")
    _trace(f"  fin_c for C={C}: no_return_psi={no_return_psi}")
    r_with = simplify_ltl(reach_strong(init, None, "false", C, no_return_psi, casc))
    _trace(f"  fin_c for C={C}: r_with={r_with}")
    fin_expr = simplify_ltl(f"!({r_to}) | ({r_with})")
    _trace(f"  fin_c for C={C}: final={fin_expr}")
    return fin_expr
