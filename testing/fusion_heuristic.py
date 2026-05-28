"""
Development file for the programmatic "fusion test" / size-2 absorption heuristic.

Goal: Given an automaton with a size-2 non-accepting SCC {A, B},
construct a new automaton that "unfolds the cycle once" so that the
result has only size-1 SCCs and is language-equivalent (when the
heuristic applies).

This version attempts to build the transformed automaton using Spot's
API instead of a hardcoded HOA string.
"""

import spot


def find_size2_nonaccepting_scc(aut):
    """Return (scc_idx, [stateA, stateB]) for the first size-2 non-acc SCC, or None."""
    si = spot.scc_info(aut)
    for scc_idx in range(si.scc_count()):
        if si.is_accepting_scc(scc_idx):
            continue
        states = list(si.states_of(scc_idx))
        if len(states) == 2:
            return scc_idx, states
    return None, None


def get_true_bdd(aut):
    """Return a bdd representing the constant true for this automaton."""
    f = spot.formula("1")
    tmp = f.translate()
    for e in tmp.out(tmp.get_init_state_number()):
        return e.cond
    # Very last resort
    return aut.get_dict().var(0) & ~aut.get_dict().var(0)   # should never happen


def try_absorb_size2_nonaccepting_scc(aut):
    """
    Programmatic "fusion test" for size-2 non-accepting SCCs.

    Attempts to unfold the cycle once following the concrete algorithm:
      - Detect size-2 non-acc SCC {A, B}
      - Create primed copies A' and B' for the first iteration
      - Relabel self-loop on the "first return" copy to true
      - Drop the return edge between the primed copies
      - Redirect the return condition from the primed copy directly
        to the accepting sink that the original SCC could reach
      - Check language equivalence
    """
    scc_idx, states = find_size2_nonaccepting_scc(aut)
    if states is None:
        return None

    print("  → Size-2 non-accepting SCC detected, building absorbed automaton programmatically...")

    A, B = states[0], states[1]

    # Collect useful information
    inside = []          # (src, dst, cond) inside the SCC
    exits = {}           # src_in_scc -> [(cond, dst_outside), ...]
    entries = []         # (src_outside, dst_in_scc, cond)

    for src in range(aut.num_states()):
        for e in aut.out(src):
            if src in (A, B) and e.dst in (A, B):
                inside.append((src, e.dst, e.cond))
            elif src in (A, B):
                if src not in exits:
                    exits[src] = []
                exits[src].append((e.cond, e.dst))
            elif e.dst in (A, B):
                entries.append((src, e.dst, e.cond))

    true_bdd = get_true_bdd(aut)

    # Try both possible orientations for which state is "first return"
    for first, second in [(A, B), (B, A)]:
        new_aut = spot.make_twa_graph(aut.get_dict())
        new_aut.set_acceptance(aut.acc())

        # Map old states to new states
        state_map = {s: new_aut.new_state() for s in range(aut.num_states())}

        # Fresh copies for the first unfolding
        first_prime = new_aut.new_state()   # copy of "first" (the one we return to)
        second_prime = new_aut.new_state()  # copy of "second"

        # Copy all edges that are completely outside the problematic SCC
        for src in range(aut.num_states()):
            for e in aut.out(src):
                if src in (A, B) or e.dst in (A, B):
                    continue
                new_aut.new_edge(state_map[src], state_map[e.dst], e.cond, e.acc)

        # Copy edges from outside into the SCC, but point them to the primed versions
        for src_out, dst_in, cond in entries:
            if dst_in == first:
                new_aut.new_edge(state_map[src_out], first_prime, cond)
            else:
                new_aut.new_edge(state_map[src_out], second_prime, cond)

        # Re-create the internal structure in unfolded form

        # 1. The "continue" self-loop that existed on one of the states is kept on the originals
        #    (for later laps if the heuristic ever wants to allow multiple iterations).
        #    For the first lap we use the primed states.

        # 2. Put a true self-loop on the "first return" primed copy (the key step)
        new_aut.new_edge(first_prime, first_prime, true_bdd)

        # 3. Find the "return condition" (the condition that used to go second -> first)
        return_cond = None
        for src, dst, cond in inside:
            if src == second and dst == first:
                return_cond = cond
                break

        # 4. Redirect that return condition from second_prime directly to the accepting sink(s)
        if return_cond is not None and first in exits:
            for cond, dst_out in exits.get(first, []):
                new_aut.new_edge(second_prime, state_map[dst_out], return_cond & cond)

        # 5. Preserve other useful internal edges in a linear way for the first lap
        #    (self-loops on the "second" state, etc.)
        for src, dst, cond in inside:
            if src == first and dst == first:
                # self-loop that existed on the "first" state
                new_aut.new_edge(first_prime, first_prime, cond)
            if src == second and dst == second:
                new_aut.new_edge(second_prime, second_prime, cond)

        # Copy any remaining edges that go from the SCC to outside that we might have missed
        for src in (A, B):
            for cond, dst_out in exits.get(src, []):
                # These are already handled for the return case above; copy others conservatively
                if src not in (first, second) or cond != return_cond:
                    new_aut.new_edge(state_map[src], state_map[dst_out], cond)

        # Set initial state
        new_aut.set_init_state(state_map[aut.get_init_state_number()])
        new_aut.copy_ap_of(aut)

        # Check if we produced something language-equivalent
        try:
            if spot.are_equivalent(aut, new_aut):
                print("  → Programmatic absorption succeeded → pseudo-linear form!")
                return new_aut
        except Exception as e:
            print(f"  → Equivalence check error: {e}")

    print("  → Could not synthesize a working absorbed automaton for this SCC.")
    return None


# -----------------------------------------------------------------------------
# Quick test on the known case
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    formula = "X(p1 | F(p1 & Xp1))"
    print("Formula:", formula)

    aut = spot.formula(formula).translate("GeneralizedBuchi", "Small", "High")
    print("Original states:", aut.num_states())

    result = try_absorb_size2_nonaccepting_scc(aut)
    if result is not None:
        print("Success! New automaton has", result.num_states(), "states")
        print("Equivalent?", spot.are_equivalent(aut, result))
    else:
        print("Heuristic did not succeed on this formula.")
