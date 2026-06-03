"""
reachability.py — High-level LTL reconstruction from 1-level cascades using the K operators.

The heavy base operators live in reachability_operators.py (smaller file, easier to maintain
and to extend for the inductive multi-level case later).

Per the refactoring plan:
- Keep the old ad-hoc logic as reconstruct_ltl_1level_buchi_heuristic for comparison.
- New reconstruct_ltl_1level_buchi is thin: mainly "from init, G F (reach some acc config)"
  built using the operators, with no (or minimal) structural pattern matching on the aut.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

# Re-export the core operators so existing callers (examples, tests) continue to work
from .reachability_operators import (  # noqa: F401
    letters_to_prop,
    make_guard,
    one_level_reach_stay,
    one_level_reach_strong,
    one_level_reach_weak,
    build_1level_reachability,
    fin_1level,
    inf_1level,
    _config_to_pos,
    _build_trans_for_pos,
)

from .cascade import Cascade


def reconstruct_ltl_1level_buchi_heuristic(casc: Cascade) -> str:
    """Old ad-hoc version (kept for comparison and fallback during the refactor).

    Contains the structural ifs (1-state, dead, init-is-acc special, B choice from acc set,
    early constant handling via original_aut, >2 unsupported string, etc.).
    Do not extend this; use it only to diff against the new clean version.
    """
    # --- BEGIN old body (unchanged from pre-refactor state) ---
    if casc.num_levels > 2:
        return "UNSUPPORTED: multi-level induction not implemented yet"

    if not casc.letter_valuations or not casc.aps:
        # constant case (no props)
        if casc.original_aut is not None:
            aut = casc.original_aut
            has_acc = any(bool(list(e.acc.sets())) for s in range(aut.num_states()) for e in aut.out(s))
            return "true" if has_acc else "false"
        return "true"

    ca = casc.build_configuration_automaton()
    states = ca["states"]
    if not states:
        return "true"

    # Map tuple configs to int positions for the 1-level K operators (SgpDec style 1-based)
    pos_map = {c: c[0] for c in states}
    rev_pos = {p: c for c, p in pos_map.items()}

    # Initial position
    init_c = None
    if casc.original_aut is not None:
        init_s = casc.original_aut.get_init_state_number()
        init_c = casc.state_to_config.get(init_s)
    if init_c is None:
        init_c = states[0]
    init_pos = pos_map.get(init_c, 1)

    # Accepting positions (int)
    acc_cs = casc.accepting_configs()
    acc_pos = [pos_map[c] for c in acc_cs if c in pos_map]
    if not acc_pos:
        # no way to accept
        return "false"

    # Build trans dict per position (int pos -> letter_idx -> next int pos)
    trans_per_pos = {}
    for c in states:
        p = pos_map[c]
        trans_per_pos[p] = {}
        for item in ca["transitions"].get(c, []):
            li, nc, _ = item
            if nc in pos_map:
                trans_per_pos[p][li] = pos_map[nc]

    # Build trans for init (for the operators)
    init_trans = trans_per_pos.get(init_pos, {})

    # Thin pure construction using K operators for liveness (visit acc i.o.)
    # Pick a target acc pos
    target = acc_pos[0]

    # Build K from init to target (using strong to avoid bad if possible)
    # B = a non-acc pos if it helps avoid traps; else 0 (no specific B)
    bads = [p for p in trans_per_pos if p not in acc_pos]
    B = bads[0] if bads else 0

    # K_init = reach from init to target with tau = the repeated from target
    # First, the inner K from target to target (for the "repeat")
    K_target = one_level_reach_strong(target, B, target, "true", casc.letter_valuations, casc.aps, trans_per_pos.get(target, {}))

    # The property after reaching target: G ( F ( K_target ) )
    prop_after_target = f"G(F({K_target}))"

    # Now the K from init to target, with the suffix property
    K_init = one_level_reach_strong(init_pos, B, target, prop_after_target, casc.letter_valuations, casc.aps, init_trans)

    # For the case where init itself is acc, we can start with the prop from init
    if init_pos in acc_pos:
        K_init = f"G(F({one_level_reach_strong(init_pos, B, init_pos, 'true', casc.letter_valuations, casc.aps, init_trans)}))"

    # The top formula is the K_init (the sequences from init that cause the first reach to target, and then the suffix satisfies the repeated reaches)
    # This uses only the K operators in a nested way for the i.o. visits.
    return K_init
    # --- END old body ---


# ---------------------------------------------------------------------------
# New clean implementation (the goal of the refactor)
# ---------------------------------------------------------------------------

def build_infinitely_often_accepting(casc: Cascade) -> str:
    """Core reusable piece for 1-level Büchi: from init, always eventually reach some accepting config.

    Expressed as G( F(reach1) | F(reach2) | ... ) using one_level_reach_strong + tau="true".
    This is the main 'intelligence' that should replace all the ad-hoc shape checks.
    """
    if casc.num_levels != 1:
        raise NotImplementedError("build_infinitely_often_accepting only for num_levels==1 (use induction for >1)")

    configs = casc.all_configs()
    if not configs:
        return "false"

    # Init config (robust)
    init_config: Optional[Tuple[int, ...]] = None
    if casc.original_aut is not None:
        try:
            init_s = casc.original_aut.get_init_state_number()
            init_config = casc.state_to_config.get(init_s)
        except Exception:
            pass
    if init_config is None:
        init_config = configs[0]

    init_pos = _config_to_pos(init_config)

    acc_configs = casc.accepting_configs()
    if not acc_configs:
        return "false"

    # Global acceptance check: if the original aut literally has no accepting transitions
    # anywhere, there are no accepting runs (e.g. the "false" constant). Do not build a
    # spurious liveness formula. This replaces the old early "constant case" structural test.
    if casc.original_aut is not None:
        aut = casc.original_aut
        has_any_acc = any(bool(list(e.acc.sets())) for s in range(aut.num_states()) for e in aut.out(s))
        if not has_any_acc:
            return "false"

    reach_parts: List[str] = []
    for acc_c in sorted(acc_configs):  # deterministic order
        acc_pos = _config_to_pos(acc_c)
        init_trans = _build_trans_for_pos(casc, init_pos)
        reach_f = one_level_reach_strong(
            S=init_pos,
            B=0,
            T=acc_pos,
            tau="true",
            valuations=casc.letter_valuations,
            aps=casc.aps,
            trans=init_trans,
        )

        # Is this acc config absorbing (all letters from it stay in it)?
        # If yes, reaching it *once* is sufficient for the Büchi obligation
        # (you will visit it i.o. or the acceptance is satisfied by permanence).
        # Expressed purely from the trans dict + K (no original aut shape inspection).
        acc_trans = _build_trans_for_pos(casc, acc_pos)
        is_absorbing = bool(acc_trans) and all(tgt == acc_pos for tgt in acc_trans.values())

        if is_absorbing:
            reach_parts.append(f"F({reach_f})")
        else:
            # May escape the acc, so we need to be able to return i.o.
            reach_parts.append(f"G(F({reach_f}))")

    if not reach_parts:
        return "false"

    inner = " | ".join(reach_parts)
    # For a disjunction of obligations, the top-level for the run is usually just the inner
    # (the G is already inside the non-absorbing terms; absorbing terms use F).
    # If all terms were absorbing we may want an outer G? but for 1-level Büchi the
    # disjunct of "eventually reach a permanent acc" is typically sufficient as the
    # "recurrence" is guaranteed by absorption.
    return inner if inner else "false"


def reconstruct_ltl_1level_buchi(casc: Cascade) -> str:
    """New clean version.

    For a 1-level Büchi the main path is:
        G( build_infinitely_often_accepting(...) )

    All special cases (dead, permanent sink, 1-config, until "q" filter, has_bad_self, etc.)
    should be expressed implicitly by the valuations + the K operators (one_level_reach_strong etc.)
    rather than by inspecting original_aut shape or hard-coded ifs.

    For num_levels != 1 we raise (future: delegate to multi-level or heuristic).
    """
    if casc.num_levels == 0:
        # Degenerate constant (e.g. "true"/"false" auts with no states in the cascade)
        if casc.original_aut is not None:
            aut = casc.original_aut
            has_acc = any(bool(list(e.acc.sets())) for s in range(aut.num_states()) for e in aut.out(s))
            return "true" if has_acc else "false"
        return "true"

    if casc.num_levels != 1:
        # For now raise; the plan keeps the heuristic available for comparison on >1 cases
        # (many current decomps with dead trap produce 2-3 levels even for simple formulas).
        raise NotImplementedError(
            f"Only 1-level supported in clean reconstruct (got {casc.num_levels}). "
            "Use reconstruct_ltl_1level_buchi_heuristic(casc) for comparison/fallback."
        )

    core = build_infinitely_often_accepting(casc)
    if core in ("false", "true"):
        return core
    # For Büchi acceptance on 1-level, the recurrence "always eventually visit acc config"
    # is typically wrapped in G(...) already inside the builder. Return as-is or adjust.
    # Some cases may want just the core if the language doesn't require the outer G for safety prefix.
    return core


__all__ = [
    "reconstruct_ltl_1level_buchi",
    "reconstruct_ltl_1level_buchi_heuristic",
    "build_infinitely_often_accepting",
    # plus the re-exports from operators
]
