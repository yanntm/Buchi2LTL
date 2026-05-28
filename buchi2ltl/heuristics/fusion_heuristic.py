"""
Clean surgical implementation of the fusion test (size-2 absorption)
following the user's precise instructions.

Set DEBUG_FUSION = True at the top of this file to enable heavy tracing
during debugging sessions.
"""

DEBUG_FUSION = False

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


def try_absorb_size2_v2(aut):
    """
    Follows the user's exact rule:
      - Print A and B indices clearly.
      - Create one new state A'.
      - Iterate transitions from A: copy ONLY those that do NOT lead to B into A'.
      - Edit outgoing edge from B to A to point to A' instead.
      - Edit outgoing edge from B to B (self-loop) to label with 1 (true).
    """
    scc, states = find_size2_nonacc_scc(aut)
    if states is None:
        return None

    if DEBUG_FUSION:
        print("  → Size-2 non-accepting SCC found. Applying precise fusion rule...")

    A, B = states[0], states[1]

    # Role assignment (A must be the one with exit to accepting)
    si = spot.scc_info(aut)

    def has_exit_to_accepting(state):
        for e in aut.out(state):
            if e.dst not in (A, B):
                if si.is_accepting_scc(si.scc_of(e.dst)):
                    return True
        return False

    if has_exit_to_accepting(A) and has_exit_to_accepting(B):
        print("  → Both states exit to accepting behavior. Skipping.")
        return None

    if has_exit_to_accepting(A):
        initiator = A
        other = B
    elif has_exit_to_accepting(B):
        initiator = B
        other = A
    else:
        print("  → No state has exit to accepting behavior.")
        return None

    # === Required clear trace ===
    if DEBUG_FUSION:
        print(f"  → Matched pattern: A = {initiator}, B = {other}")

    true_bdd = get_true_bdd(aut)

    # Start fresh - we will only add the edges we want
    new_aut = spot.make_twa_graph(aut.get_dict())
    new_aut.set_acceptance(aut.acc())

    state_map = {s: new_aut.new_state() for s in range(aut.num_states())}

    # Copy edges that are completely outside the {A, B} SCC.
    # We deliberately skip all internal edges of the size-2 SCC so we don't
    # carry over the bad B → A edge and the old self-loop on B.
    for src in range(aut.num_states()):
        for e in aut.out(src):
            if src in (A, B) and e.dst in (A, B):
                cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
                if src == initiator and e.dst == other:
                    # This is the A → B edge used for the first loop iteration. Keep it.
                    print(f"     [KEEP during copy] Internal edge A --[{cond_str}]--> B (first loop iteration edge)")
                    new_aut.new_edge(state_map[src], state_map[e.dst], e.cond, e.acc)
                else:
                    print(f"     [SKIP during copy] Internal SCC edge: {src} --[{cond_str}]--> {e.dst}")
                    continue
            else:
                new_aut.new_edge(state_map[src], state_map[e.dst], e.cond, e.acc)

    # 1. Create the new state A' (copy of A / initiator)
    A_prime = new_aut.new_state()
    if DEBUG_FUSION:
        print(f"  → Created new state A' with index {A_prime}")

    # 2. Iterate transitions from A: copy ONLY those that do NOT lead to B into A'
    if DEBUG_FUSION:
        print("  → Iterating transitions from A, copying only those not leading to B into A':")
    for e in aut.out(initiator):
        if e.dst == other:
            if DEBUG_FUSION:
                cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
                print(f"     [SKIP for A'] A --[{cond_str}]--> B   (per algorithm: only copy transitions from A that do not lead to B into A')")
            continue
        new_aut.new_edge(A_prime, state_map[e.dst], e.cond, e.acc)
        if DEBUG_FUSION:
            cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
            print(f"     [COPY] A'={A_prime} --[{cond_str}]--> {e.dst}")

    # 3. Edit outgoing edge from B to A → point to A' instead
    if DEBUG_FUSION:
        print("  → Editing outgoing edge from B to A to point to A' instead:")
    for e in aut.out(other):
        if e.dst == initiator:
            if DEBUG_FUSION:
                cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
                print(f"     [EDIT] B={state_map[other]} --[{cond_str}]--> A   →   B --> A'={A_prime}")
            new_aut.new_edge(state_map[other], A_prime, e.cond, e.acc)

    # 4. Edit outgoing edge from B to B (self-loop) → label with 1 (true)
    if DEBUG_FUSION:
        print("  → Editing self-loop from B to B to label 1 (true):")
    for e in aut.out(other):
        if e.dst == other:
            if DEBUG_FUSION:
                cond_str = spot.bdd_format_formula(aut.get_dict(), e.cond)
                print(f"     [EDIT] B self-loop was [{cond_str}], now labeled 1 (true)")
            new_aut.new_edge(state_map[other], state_map[other], true_bdd, e.acc)

    new_aut.set_init_state(state_map[aut.get_init_state_number()])
    new_aut.copy_ap_of(aut)

    try:
        if spot.are_equivalent(aut, new_aut):
            if DEBUG_FUSION:
                print("  → Absorption succeeded (clean surgical version)!")
            return new_aut
        else:
            if DEBUG_FUSION:
                print("  → Not yet equivalent.")
            return new_aut
    except Exception as e:
        if DEBUG_FUSION:
            print(f"  → Equivalence error: {e}")
        return new_aut


# Quick test
if __name__ == "__main__":
    formula = "X(p1 | F(p1 & Xp1))"
    print("Testing clean surgical v2 on:", formula)
    aut = spot.formula(formula).translate("GeneralizedBuchi", "Small", "High")
    result = try_absorb_size2_v2(aut)
    if result:
        print("Success! New states:", result.num_states())
        print("Equivalent?", spot.are_equivalent(aut, result))
    else:
        print("Heuristic did not succeed.")
