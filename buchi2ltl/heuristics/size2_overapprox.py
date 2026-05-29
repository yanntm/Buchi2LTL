"""
Size-2 Non-Accepting SCC Over-Approximation Heuristic (f2).

This heuristic detects non-accepting SCCs consisting of exactly two states
and attempts to "unfold" them once into a pseudo-linear structure.

The key operation is relabeling a self-loop with `true` (full alphabet).
This is a deliberate over-approximation: it can add behaviors that were
not present in the original automaton. We only accept the result if
`spot.are_equivalent(original, transformed)` still holds.

When successful, the resulting automaton has only size-1 SCCs and can be
fed to the core backward labeling procedure.

Implementation note: the core surgical rewrite (the version that correctly
handles cases such as "X(p1 | F(p1 & Xp1))") was developed through
experimentation and is now the canonical implementation in this module.
The public API (try_size2_overapprox) and strict equivalence gate are
preserved.
"""

import os
import spot

# Tracing for the f2 / size-2 over-approx heuristic.
# Enable with RECONSTRUCT_TRACE=1 (consistent with main reconstruction and t2)
# or the more specific F2_TRACE=1.
F2_TRACE = os.environ.get("RECONSTRUCT_TRACE") == "1" or os.environ.get("F2_TRACE") == "1"

# Legacy debug flag kept for compatibility but now tied to the new tracing.
DEBUG_SIZE2_OVERAPPROX = F2_TRACE


def find_size2_nonacc_scc(aut):
    si = spot.scc_info(aut)
    for scc in range(si.scc_count()):
        if si.is_accepting_scc(scc):
            continue
        states = list(si.states_of(scc))
        if len(states) == 2:
            if F2_TRACE:
                print(f"[F2] Found size-2 non-accepting SCC #{scc}: states={states}")
                print("[F2]   (State numbers match trace_aut_before_f2.png / .dot)")
            return scc, states
    if F2_TRACE:
        print("[F2] No size-2 non-accepting SCC found.")
    return None, None


def get_true_bdd(aut):
    f = spot.formula("1")
    tmp = f.translate()
    for e in tmp.out(tmp.get_init_state_number()):
        return e.cond
    raise RuntimeError("Could not create true bdd")


def try_size2_overapprox(aut):
    """
    Main entry point for the size-2 over-approximation heuristic.

    Returns the transformed automaton if successful and language-equivalent,
    otherwise returns None.
    """
    scc, states = find_size2_nonacc_scc(aut)
    if states is None:
        return None

    if F2_TRACE:
        print("[F2] Size-2 non-accepting SCC found. Starting over-approximation rewrite...")

    A, B = states[0], states[1]

    # Role detection: A must be the one with an exit to accepting behavior
    si = spot.scc_info(aut)

    def has_exit_to_accepting(state):
        for e in aut.out(state):
            if e.dst not in (A, B):
                if si.is_accepting_scc(si.scc_of(e.dst)):
                    return True
        return False

    exit_A = has_exit_to_accepting(A)
    exit_B = has_exit_to_accepting(B)
    if F2_TRACE:
        print(f"[F2]   has_exit_to_accepting({A}) = {exit_A}")
        print(f"[F2]   has_exit_to_accepting({B}) = {exit_B}")

    if exit_A and exit_B:
        if F2_TRACE:
            print("[F2]   Both states have exits to accepting behavior. Skipping (not the expected pattern).")
        return None

    if exit_A:
        initiator = A
        other = B
    elif exit_B:
        initiator = B
        other = A
    else:
        if F2_TRACE:
            print("[F2]   Neither state has an exit to an accepting SCC. No pattern match.")
        return None

    if F2_TRACE:
        print(f"[F2]   Role assignment: initiator={initiator}, other={other} (the one whose self-loop will be over-approximated)")

    true_bdd = get_true_bdd(aut)
    true_str = spot.bdd_format_formula(aut.get_dict(), true_bdd)
    if F2_TRACE:
        print(f"[F2]   true BDD for over-approximation: {true_str}")

    # Build the transformed automaton (surgical version from the
    # verified implementation of the size-2 absorption heuristic).
    new_aut = spot.make_twa_graph(aut.get_dict())
    new_aut.set_acceptance(aut.acc())

    state_map = {s: new_aut.new_state() for s in range(aut.num_states())}

    if F2_TRACE:
        print("[F2]   --- Edge copy phase (deliberately dropping most internal edges of the 2-SCC) ---")

    # Copy edges that are completely outside the {A, B} SCC.
    # We deliberately skip most internal edges of the size-2 SCC, but we
    # MUST preserve the initiator → other edge (the "first loop iteration"
    # A → B edge).  This edge is semantically required for the transformed
    # automaton to remain language-equivalent on cases such as
    # "X(p1 | F(p1 & Xp1))".
    for src in range(aut.num_states()):
        for e in aut.out(src):
            if src in (A, B) and e.dst in (A, B):
                if src == initiator and e.dst == other:
                    # Keep the critical first-unfolding edge from initiator into the other state.
                    new_aut.new_edge(state_map[src], state_map[e.dst], e.cond, e.acc)
                    if F2_TRACE:
                        cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
                        print(f"[F2]     [KEEP] First-loop edge {src} --[{cond_str}]--> {e.dst}")
                else:
                    if F2_TRACE:
                        cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
                        print(f"[F2]     [SKIP internal] {src} --[{cond_str}]--> {e.dst}")
                    continue
            else:
                new_aut.new_edge(state_map[src], state_map[e.dst], e.cond, e.acc)

    # Create A' (copy of the initiator) — this is the "unfolded" version
    A_prime = new_aut.new_state()
    if F2_TRACE:
        print(f"[F2]   Created new state A' (index {A_prime}) — unfolded copy of initiator")

    # Copy transitions from initiator that do NOT lead to the other state into A'
    if F2_TRACE:
        print("[F2]   Copying initiator's non-to-other exits into A':")
    for e in aut.out(initiator):
        if e.dst == other:
            if F2_TRACE:
                cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
                print(f"[F2]     [SKIP for A'] {initiator} --[{cond_str}]--> {other}")
            continue
        new_aut.new_edge(A_prime, state_map[e.dst], e.cond, e.acc)
        if F2_TRACE:
            cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
            print(f"[F2]     [COPY] A'={A_prime} --[{cond_str}]--> {e.dst}")

    # Redirect B → A (other → initiator) edges to point to A' instead
    if F2_TRACE:
        print("[F2]   Redirecting other→initiator edges to other→A' :")
    for e in aut.out(other):
        if e.dst == initiator:
            new_aut.new_edge(state_map[other], A_prime, e.cond, e.acc)
            if F2_TRACE:
                cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
                print(f"[F2]     [EDIT] Redirect {other} --> {initiator}  to  {other} --> A'   (cond={cond_str})")

    # === THE KEY OVER-APPROXIMATION ===
    # Relabel the other state's self-loop with true (full alphabet).
    # This is the "raw guess" / deliberate over-approximation.
    # It can add behaviors. We only keep the result if the language-equivalence
    # check later says the overall language is still the same.
    if F2_TRACE:
        print("[F2]   === OVER-APPROXIMATION STEP ===")
        print("[F2]   Relabeling the 'other' state's self-loop with true (full alphabet)")
    for e in aut.out(other):
        if e.dst == other:
            new_aut.new_edge(state_map[other], state_map[other], true_bdd, e.acc)
            if F2_TRACE:
                print(f"[F2]     [OVER-APPROX] {other} self-loop: original cond replaced by TRUE ({true_str})")
            break

    new_aut.set_init_state(state_map[aut.get_init_state_number()])
    new_aut.copy_ap_of(aut)

    if F2_TRACE:
        print(f"[F2]   Rewritten automaton has {new_aut.num_states()} states (original had {aut.num_states()})")
        print("[F2]   === LANGUAGE EQUIVALENCE VALIDATION (the soundness gate) ===")
        print("[F2]   Checking spot.are_equivalent(original, over_approx_rewritten) ...")

    try:
        eq = spot.are_equivalent(aut, new_aut)
        if F2_TRACE:
            print(f"[F2]   are_equivalent result = {eq}")
        if eq:
            if F2_TRACE:
                print("[F2]   ✓ Over-approximation accepted (language preserved). Returning massaged automaton.")
            return new_aut
        else:
            if F2_TRACE:
                print("[F2]   ✗ Produced non-equivalent automaton; rejecting the rewrite.")
            return None
    except Exception as e:
        if F2_TRACE:
            print(f"[F2]   Equivalence check raised exception: {e}")
        return None
