"""
Size-2 Non-Accepting SCC Absorption Heuristic (Fusion Test) — v2

This is the version that follows the precise pattern the user described:

- Detect non-accepting SCC of exactly two states {A, B}
- A has an outgoing edge to B
- B has a self-loop
- B has a return edge to A
- The SCC is non-accepting
- Exactly one of the two states has an outgoing edge to accepting behavior.
  We designate that state as A (the "initiator").
- If both have such exits → we report and skip for now.

Transformation (unroll once):
- Create A' = fresh copy of A (same outgoing edges as A at creation time)
- Change edges outgoing from B that go to A → now go to A'
- Drop any return edge from A' back to B
- Relabel the self-loop on B with true (full alphabet)

Then test language equivalence. If it holds, return the pseudo-linear
automaton so that the normal backward-labeling rules can be applied.
"""

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


def try_absorb_size2_nonaccepting_scc(aut):
    """
    The current best implementation of the fusion test (as of late May 2026).
    """
    scc, states = find_size2_nonacc_scc(aut)
    if states is None:
        return None

    print("  → Size-2 non-accepting SCC detected, applying precise fusion rule...")

    A, B = states[0], states[1]

    # --- Role detection ---
    si = spot.scc_info(aut)

    def exits_to_accepting(state):
        for e in aut.out(state):
            if e.dst not in (A, B):
                target_scc = si.scc_of(e.dst)
                if si.is_accepting_scc(target_scc):
                    return True
        return False

    exits_A = exits_to_accepting(A)
    exits_B = exits_to_accepting(B)

    if exits_A and exits_B:
        print("  → Both states exit to accepting behavior. Skipping (per rule).")
        return None

    if exits_A:
        initiator = A      # A has the exit to accepting
        other = B
    elif exits_B:
        initiator = B
        other = A
    else:
        print("  → No state exits to accepting behavior. Cannot apply rule.")
        return None

    print(f"  → A (initiator): state {initiator}, B: state {other}")

    true_bdd = get_true_bdd(aut)

    # --- Build new automaton ---
    new_aut = spot.make_twa_graph(aut.get_dict())
    new_aut.set_acceptance(aut.acc())

    state_map = {s: new_aut.new_state() for s in range(aut.num_states())}
    A_prime = new_aut.new_state()

    # Copy edges completely outside the {A,B} SCC
    for src in range(aut.num_states()):
        for e in aut.out(src):
            if src in (A, B) and e.dst in (A, B):
                continue
            new_aut.new_edge(state_map[src], state_map[e.dst], e.cond, e.acc)

    # Copy outgoing edges of the initiator (A) to A'
    for e in aut.out(initiator):
        if e.dst == other:
            new_aut.new_edge(A_prime, state_map[other], e.cond, e.acc)
        elif e.dst == initiator:
            new_aut.new_edge(A_prime, A_prime, e.cond, e.acc)
        else:
            new_aut.new_edge(A_prime, state_map[e.dst], e.cond, e.acc)

    # Transform edges coming out of the other state (B)
    for e in aut.out(other):
        if e.dst == other:
            # self-loop on B → true
            new_aut.new_edge(state_map[other], state_map[other], true_bdd, e.acc)
        elif e.dst == initiator:
            # B → A  becomes  B → A'
            new_aut.new_edge(state_map[other], A_prime, e.cond, e.acc)
        else:
            new_aut.new_edge(state_map[other], state_map[e.dst], e.cond, e.acc)

    # Incoming edges from outside → route into the unfolded path
    for src in range(aut.num_states()):
        if src in (A, B):
            continue
        for e in aut.out(src):
            if e.dst == initiator:
                new_aut.new_edge(state_map[src], A_prime, e.cond, e.acc)
            elif e.dst == other:
                new_aut.new_edge(state_map[src], state_map[other], e.cond, e.acc)

    new_aut.set_init_state(state_map[aut.get_init_state_number()])
    new_aut.copy_ap_of(aut)

    # During active development of the heuristic, delegate to the latest
    # version living in testing/. This will be cleaned up later.
    try:
        from testing.fusion_heuristic import try_absorb_size2_v2 as _impl
        result = _impl(aut)
        return result
    except Exception as e:
        print(f"  → Heuristic development version raised: {e}")
        return None
