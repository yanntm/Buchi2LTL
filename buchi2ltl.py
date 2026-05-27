import spot

# =============================================================================
# PROTOTYPE: Backward LTL reconstruction from TGBA (your exact idea)
# =============================================================================
# This version follows the rules you described on the HOA example:
#
#   For a pure self-loop accepting state:
#       G(OR of every outgoing label)  &  GF(OR of labels on accepting edges)
#
#   For states with exits:
#       Use Until, and when accepting self-loops exist, also allow the
#       "stay forever satisfying acceptance" disjunct.
# =============================================================================

def ltl_to_tgba(ltl_str):
    """Translate LTL → TGBA."""
    f = spot.formula(ltl_str)
    aut = f.translate("GeneralizedBuchi", "Small", "High")
    print(f"Original LTL : {ltl_str}")
    print(f"States       : {aut.num_states()}")
    print(f"Acceptance   : {aut.get_acceptance()}")
    return aut, f


def reconstruct_ltl(aut):
    """
    Backward reconstruction of LTL from the TGBA, following your manual rules.

    - Process states only after all their non-self successors are labeled.
    - Pure accepting self-loop states → G(OR_all) & GF(OR_acc)
    - Mixed states → (G(self) & GF(acc)) | (self U exit)   or plain Until
    """
    state_formula = {}

    # Dependency-driven backward labeling (robust to SCC numbering)
    remaining = set(range(aut.num_states()))
    while remaining:
        progress = False

        for q in list(remaining):
            # Ready only when every non-self successor already has a formula
            if any(e.src != e.dst and e.dst not in state_formula for e in aut.out(q)):
                continue

            self_loops = []   # (cond_str, carries_acc)
            exits = []        # (succ_formula_str)  -- already with label & X()

            for e in aut.out(q):
                cond = spot.bdd_format_formula(aut.get_dict(), e.cond)
                carries = bool(list(e.acc.sets()))

                if e.src == e.dst:
                    self_loops.append((cond, carries))
                else:
                    succ = state_formula[e.dst]
                    if cond == "1":
                        exits.append(f"X({succ})")
                    else:
                        exits.append(f"({cond}) & X({succ})")

            # --- Pure self-loop state (your rule) ---
            if not exits and self_loops:
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

                state_formula[q] = phi
                remaining.remove(q)
                progress = True
                continue

            # --- State with exits ---
            if exits:
                or_ex = " | ".join(exits)
                if len(exits) > 1:
                    or_ex = f"({or_ex})"

                has_acc = any(carries for _, carries in self_loops)

                if has_acc:
                    # Can remain here forever and still accept
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

                state_formula[q] = phi
                remaining.remove(q)
                progress = True
                continue

            # No outgoing at all (very rare)
            state_formula[q] = "false"
            remaining.remove(q)
            progress = True

    # Result from the initial state
    init = aut.get_init_state_number()
    final = state_formula[init]

    # Light syntactic cleanup + real simplification via Spot
    final = final.replace(" & X(true)", " X true")
    final = final.replace("X(true)", "X true")
    final = final.replace("G(true)", "G true")
    final = final.replace("G(1)", "G true")

    # Ask Spot to simplify the formula we built (produces much nicer output)
    try:
        simplified = spot.formula(final).simplify()
        final = str(simplified)
    except Exception:
        pass

    return final, state_formula


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    test_cases = [
        "(p U q) & GF r",
        "FG a",
        "a U b",
        "G (p -> X p) & GF q",
        "GF (p & q) & G (r -> X r)",
        "(a U b) & (c U d) & GF e",
    ]

    for original_str in test_cases:
        print("\n" + "=" * 80)
        aut, original_f = ltl_to_tgba(original_str)

        recovered_str, state_formulas = reconstruct_ltl(aut)

        print(f"Recovered LTL : {recovered_str}")
        print("State formulas:")
        for q, phi in sorted(state_formulas.items()):
            print(f"  state {q:2d} → {phi}")

        recovered_f = spot.formula(recovered_str)
        equivalent = spot.are_equivalent(original_f, recovered_f)
        print(f"Semantically equivalent ? {equivalent}")
        if not equivalent:
            print("   → reconstruction failed (not yet equivalent)")
        else:
            print("   → Perfect match!")
