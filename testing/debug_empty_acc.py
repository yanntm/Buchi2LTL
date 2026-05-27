#!/usr/bin/env python3
"""
Quick debug script for the "empty acceptance sets" idea.

Idea from user:
  If the automaton has 0 acceptance sets (Acceptance: t),
  reinterpret it as if there is one acceptance set and EVERY transition carries it.
  This makes self-loops look "accepting", so our existing G/GF rules can fire
  and allow "stay forever" options, which is needed for very-weak automata like W.

This is a pragmatic normalization to avoid special-casing 0-acc automata
everywhere in the reconstruction logic.
"""

import spot

def reconstruct_ltl_with_empty_acc_hack(aut):
    """
    Version of the safe reconstructor with the proposed hack:
    If aut has 0 acceptance sets, treat every transition as carrying acc.
    """
    si = spot.scc_info(aut)

    # Bad = multi-state SCCs (unchanged safety net)
    bad_states = set()
    for scc_idx in range(si.scc_count()):
        states = list(si.states_of(scc_idx))
        if len(states) > 1:
            for q in states:
                bad_states.add(q)

    # === THE HACK ===
    num_acc_sets = aut.acc().num_sets()
    treat_all_as_accepting = (num_acc_sets == 0)

    state_formula = {}
    visiting = set()
    MAX_DEPTH = 10000
    depth = [0]
    UNSUPPORTED = "UNSUPPORTED: non-trivial cycle or complex SCC"

    def label(q):
        if q in state_formula:
            return state_formula[q]
        if q in bad_states:
            state_formula[q] = UNSUPPORTED
            return UNSUPPORTED
        if q in visiting:
            state_formula[q] = UNSUPPORTED
            return UNSUPPORTED
        if depth[0] > MAX_DEPTH:
            state_formula[q] = UNSUPPORTED
            return UNSUPPORTED

        visiting.add(q)
        depth[0] += 1

        self_loops = []
        exit_terms = []

        for e in aut.out(q):
            cond = spot.bdd_format_formula(aut.get_dict(), e.cond)

            # === THE KEY CHANGE ===
            if treat_all_as_accepting:
                carries = True
            else:
                carries = bool(list(e.acc.sets()))

            if e.src == e.dst:
                self_loops.append((cond, carries))
            else:
                if e.dst in bad_states:
                    state_formula[q] = UNSUPPORTED
                    visiting.remove(q)
                    depth[0] -= 1
                    return UNSUPPORTED

                succ_phi = label(e.dst)
                if isinstance(succ_phi, str) and succ_phi.startswith("UNSUPPORTED"):
                    state_formula[q] = UNSUPPORTED
                    visiting.remove(q)
                    depth[0] -= 1
                    return UNSUPPORTED

                if cond == "1":
                    exit_terms.append(f"X({succ_phi})")
                else:
                    exit_terms.append(f"({cond}) & X({succ_phi})")

        # Apply rules (now self-loops in 0-acc automata will have carries=True)
        if not exit_terms and self_loops:
            or_all = " | ".join(f"({c})" for c, _ in self_loops)
            if len(self_loops) > 1:
                or_all = f"({or_all})"
            acc_cs = [c for c, carries in self_loops if carries]
            if acc_cs:
                or_acc = " | ".join(f"({c})" for c in acc_cs)
                if len(acc_cs) > 1:
                    or_acc = f"({or_acc})"
                phi = f"G({or_all}) & GF({or_acc})"
            else:
                phi = f"G({or_all})"

        elif exit_terms:
            or_ex = " | ".join(exit_terms)
            if len(exit_terms) > 1:
                or_ex = f"({or_ex})"
            has_acc = any(carries for _, carries in self_loops)

            if has_acc:
                acc_cs = [c for c, carries in self_loops if carries]
                or_acc = " | ".join(f"({c})" for c in acc_cs) if acc_cs else "true"
                if len(acc_cs) > 1:
                    or_acc = f"({or_acc})"
                or_self = " | ".join(f"({c})" for c, _ in self_loops)
                if len(self_loops) > 1:
                    or_self = f"({or_self})"
                stay = f"G({or_self}) & GF({or_acc})"
                phi = f"({stay}) | ({or_self} U ({or_ex}))"
            else:
                if self_loops:
                    or_self = " | ".join(f"({c})" for c, _ in self_loops)
                    if len(self_loops) > 1:
                        or_self = f"({or_self})"
                    phi = f"({or_self}) U ({or_ex})"
                else:
                    phi = or_ex
        else:
            phi = "false"

        state_formula[q] = phi
        visiting.remove(q)
        depth[0] -= 1
        return phi

    init = aut.get_init_state_number()
    final = label(init)

    if not (isinstance(final, str) and final.startswith("UNSUPPORTED")):
        final = final.replace(" & X(true)", " X true")
        final = final.replace("X(true)", "X true")
        final = final.replace("G(true)", "G true")
        final = final.replace("G(1)", "G true")
        try:
            final = str(spot.formula(final).simplify())
        except Exception:
            pass

    return final, dict(state_formula), treat_all_as_accepting


# =============================================================================
# Test on the problematic example
# =============================================================================

hoa_text = """HOA: v1
name: "!p1 W p0"
States: 2
Start: 1
AP: 2 "p1" "p0"
acc-name: all
Acceptance: 0 t
properties: trans-labels explicit-labels trans-acc deterministic
properties: stutter-invariant very-weak
--BODY--
State: 0
[t] 0
State: 1
[1] 0
[!0&!1] 1
--END--
"""

print("=== Testing the 'empty acc sets → treat everything as accepting' hack ===\n")

aut = spot.automaton(hoa_text)
print("Acceptance condition:", aut.get_acceptance())
print("Number of acc sets :", aut.acc().num_sets())
print()

final, per_state, used_hack = reconstruct_ltl_with_empty_acc_hack(aut)

print("Hack was triggered (0 acc sets):", used_hack)
print()

print("Per-state labels (raw):")
for q in sorted(per_state):
    print(f"  state {q}: {per_state[q]}")

print("\nFinal recovered formula:")
print(final)

orig = spot.formula("!p1 W p0")
rec_f = spot.formula(final) if not final.startswith("UNSUPPORTED") else None
print(f"\nEquivalent to !p1 W p0 ? {spot.are_equivalent(orig, rec_f) if rec_f else False}")

print("\n--- User's expected ---")
print("state 0 : True")
print("state 1 : (!p0 & !p1) U (p0 & X True)")
print("Expected top-level: something equivalent to !p1 W p0 (allows staying in 1 forever)")
