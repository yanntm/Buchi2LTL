#!/usr/bin/env python3
"""
Temporary test script (in testing/ folder).

Verifies whether the safe finite-recursion version preserves the behavior
on the exact cases that previously worked.

Key fix in this version: the "bad SCC" detector is now much more precise.
We only reject SCCs that have more than one state (multi-state SCCs).
This matches the original assumption "Accepting SCCs are single states with only self-loops"
and "no complex cycles inside SCCs", while still allowing states to have
exit edges to *other* SCCs (which is normal and was present in all the
cases that used to work).
"""

import spot

def reconstruct_ltl_safe(aut):
    """
    Safe version with guaranteed finite recursion.

    Detects non-trivial structure using SCCs:
      - Any SCC with more than 1 state is considered unsupported for now.
      - We also keep the visiting-set guard and a hard depth limit.
    """
    si = spot.scc_info(aut)

    # A "bad" state lives in an SCC that has multiple states.
    # This is the main source of non-self-loop cycles that can cause
    # deep or infinite recursion under the current rules.
    bad_states = set()
    for scc_idx in range(si.scc_count()):
        states = list(si.states_of(scc_idx))
        if len(states) > 1:
            for q in states:
                bad_states.add(q)

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

        # Apply the user's reconstruction rules (only reached on supported structure)
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

    return final, state_formula


# =============================================================================
# The exact cases that had worked before
# =============================================================================

KNOWN_LTL_CASES = [
    "(p U q) & GF r",
    "FG a",
    "a U b",
    "G (p -> X p) & GF q",
]

USER_FIRST_HOA = """HOA: v1
name: "(p U q) & GFr"
States: 2
Start: 0
AP: 3 "p" "q" "r"
acc-name: Buchi
Acceptance: 1 Inf(0)
properties: trans-labels explicit-labels trans-acc deterministic
properties: stutter-invariant
--BODY--
State: 0
[0&!1] 0
[1] 1
State: 1
[!2] 1
[2] 1 {0}
--END--
"""

USER_SECOND_HOA = """HOA: v1
name: "G(Fq & (!p | Xp))"
States: 2
Start: 0
AP: 2 "q" "p"
acc-name: Buchi
Acceptance: 1 Inf(0)
properties: trans-labels explicit-labels trans-acc deterministic
--BODY--
State: 0
[!0&!1] 0
[0&!1] 0 {0}
[1] 1
State: 1
[!0&1] 1
[0&1] 1 {0}
--END--
"""


def main():
    print("=== Verification: safe reconstruct_ltl on previously working cases ===\n")

    passed = 0
    for ltl in KNOWN_LTL_CASES:
        print(f"LTL: {ltl}")
        aut = spot.formula(ltl).translate("GeneralizedBuchi", "Small", "High")
        recovered, _ = reconstruct_ltl_safe(aut)
        orig = spot.formula(ltl)

        if recovered.startswith("UNSUPPORTED"):
            print(f"  -> UNSUPPORTED (would have broken a previously good case)")
        else:
            eq = spot.are_equivalent(orig, spot.formula(recovered))
            print(f"  Recovered: {recovered}")
            print(f"  Equivalent? {eq}")
            if eq:
                passed += 1

    print("\n" + "="*70)
    print("HOA 1 (user's original motivating example): (p U q) & GF r")
    aut = spot.automaton(USER_FIRST_HOA)
    rec, _ = reconstruct_ltl_safe(aut)
    print(f"  Recovered: {rec}")
    if not rec.startswith("UNSUPPORTED"):
        # We know from history this one used to be equivalent
        orig = spot.formula("(p U q) & GF r")
        print(f"  Equivalent to original? {spot.are_equivalent(orig, spot.formula(rec))}")

    print("\n" + "="*70)
    print("HOA 2 (the second one user gave): G (p -> X p) & GF q")
    aut = spot.automaton(USER_SECOND_HOA)
    rec, _ = reconstruct_ltl_safe(aut)
    print(f"  Recovered: {rec}")

    print("\n" + "="*70)
    print(f"Result: {passed} / {len(KNOWN_LTL_CASES)} simple LTL cases still fully equivalent and not rejected.")


if __name__ == "__main__":
    main()
