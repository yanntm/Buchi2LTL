"""
Size-2 Non-Accepting SCC Over-Approximation Heuristic.

This heuristic detects non-accepting SCCs consisting of exactly two states
and attempts to "unfold" them once into a pseudo-linear structure.

The key operation is relabeling a self-loop with `true` (full alphabet).
This is a deliberate over-approximation: it can add behaviors that were
not present in the original automaton. We only accept the result if
`spot.are_equivalent(original, transformed)` still holds.

When successful, the resulting automaton has only size-1 SCCs and can be
fed to the core backward labeling procedure.
"""

DEBUG_SIZE2_OVERAPPROX = False

import spot


def find_size2_nonacc_scc(aut):
    si = spot.scc_info(aut)
    for scc in range(si.scc_count()):
        if si.is_accepting_scc(scc):
            continue
        states = list(si.states_of(scc))
        if len(states) == 2:
            return scc, states
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

    if DEBUG_SIZE2_OVERAPPROX:
        print("  → Size-2 non-accepting SCC found. Applying size2_overapprox...")

    A, B = states[0], states[1]

    # Role detection: A must be the one with an exit to accepting behavior
    si = spot.scc_info(aut)

    def has_exit_to_accepting(state):
        for e in aut.out(state):
            if e.dst not in (A, B):
                if si.is_accepting_scc(si.scc_of(e.dst)):
                    return True
        return False

    if has_exit_to_accepting(A) and has_exit_to_accepting(B):
        if DEBUG_SIZE2_OVERAPPROX:
            print("  → Both states have exits to accepting behavior. Skipping.")
        return None

    if has_exit_to_accepting(A):
        initiator = A
        other = B
    elif has_exit_to_accepting(B):
        initiator = B
        other = A
    else:
        return None

    if DEBUG_SIZE2_OVERAPPROX:
        print(f"  → Matched pattern: A = {initiator}, B = {other}")

    true_bdd = get_true_bdd(aut)

    # Build the transformed automaton
    new_aut = spot.make_twa_graph(aut.get_dict())
    new_aut.set_acceptance(aut.acc())

    state_map = {s: new_aut.new_state() for s in range(aut.num_states())}

    # Copy edges that are not internal to the size-2 SCC
    for src in range(aut.num_states()):
        for e in aut.out(src):
            if src in (A, B) and e.dst in (A, B):
                continue
            new_aut.new_edge(state_map[src], state_map[e.dst], e.cond, e.acc)

    # Create A' (copy of the initiator)
    A_prime = new_aut.new_state()
    if DEBUG_SIZE2_OVERAPPROX:
        print(f"  → Created new state A' with index {A_prime}")

    # Copy transitions from A that do not go to B into A'
    for e in aut.out(initiator):
        if e.dst == other:
            if DEBUG_SIZE2_OVERAPPROX:
                cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
                print(f"     [SKIP for A'] A --[{cond_str}]--> B")
            continue
        new_aut.new_edge(A_prime, state_map[e.dst], e.cond, e.acc)
        if DEBUG_SIZE2_OVERAPPROX:
            cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
            print(f"     [COPY] A'={A_prime} --[{cond_str}]--> {e.dst}")

    # Redirect B → A edges to B → A'
    for e in aut.out(other):
        if e.dst == initiator:
            new_aut.new_edge(state_map[other], A_prime, e.cond, e.acc)
            if DEBUG_SIZE2_OVERAPPROX:
                cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
                print(f"     [EDIT] Redirect B --> A to B --> A' (cond={cond_str})")

    # Relabel B's self-loop with true (this is the over-approximating step)
    for e in aut.out(other):
        if e.dst == other:
            new_aut.new_edge(state_map[other], state_map[other], true_bdd, e.acc)
            if DEBUG_SIZE2_OVERAPPROX:
                print("     [EDIT] Relabeled B self-loop with true (over-approximation)")

    new_aut.set_init_state(state_map[aut.get_init_state_number()])
    new_aut.copy_ap_of(aut)

    try:
        if spot.are_equivalent(aut, new_aut):
            if DEBUG_SIZE2_OVERAPPROX:
                print("  → size2_overapprox succeeded and preserved language.")
            return new_aut
        else:
            if DEBUG_SIZE2_OVERAPPROX:
                print("  → size2_overapprox produced a non-equivalent automaton.")
            return None
    except Exception as e:
        if DEBUG_SIZE2_OVERAPPROX:
            print(f"  → Equivalence check failed: {e}")
        return None


# Backward compatibility alias (can be removed later)
try_absorb_size2_nonaccepting_scc = try_size2_overapprox
