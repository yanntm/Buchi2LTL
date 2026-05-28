import spot

# =============================================================================
# PROTOTYPE: Backward LTL reconstruction from TGBA
# =============================================================================
#
# This is an experimental prototype, not a complete algorithm.
#
# Core idea (from manual reconstruction rules):
#   - Process states backward (from accepting sinks toward the initial state).
#   - For pure self-loop accepting SCCs:
#         G(OR of all self-loop labels) & GF(OR of labels on accepting edges)
#   - For states with exits:
#         (G(self) & GF(acc)) | (self U exit)     when staying forever is possible
#         or plain (self U exit)                  otherwise
#
# Current limitations / design decisions:
#   - We only handle "linear-ish" TGBAs (the kind produced by many simple LTL
#     formulas). We explicitly reject automata containing multi-state SCCs.
#   - Recursion is made safe via an explicit `visiting` set (recursion stack)
#     plus an upfront multi-state SCC filter. This guarantees finite recursion.
#   - Trivial acceptance (`Acceptance: t`, 0 acceptance sets) is normalized
#     by treating every transition as accepting. This allows the existing
#     rules to handle very-weak automata (e.g. those coming from W, R, M).
#   - The procedure is INCOMPLETE BY DESIGN. Many formulas will produce
#     "UNSUPPORTED" or semantically incorrect results.
#
# The goal is to explore the space of what can be recovered by simple
# backward labeling rules before moving to more sophisticated techniques
# (cycle extraction + linearization, etc.).
#
# Heuristic layer (new):
#   - Before the main backward labeling, we attempt the "fusion test":
#     absorption of size-2 non-accepting SCCs into a pseudo-linear form.
#     This is a practical, example-driven transformation that "unfolds"
#     the most common small cycle pattern seen in LTL-derived automata
#     so that the existing U/G-based rules can be applied.
# =============================================================================


def try_absorb_size2_nonaccepting_scc(aut):
    """
    Programmatic "fusion test" (absorption heuristic) for size-2 non-accepting SCCs.

    Follows the concrete algorithm:
      1. Detect non-accepting SCC with exactly two states {A, B}.
      2. Unfold once: create fresh copies (B' of B, A' of A).
      3. Relabel self-loop on the "first return" copy (A') to true.
      4. Drop the return edge B' → A'.
      5. Redirect the return-condition from B' directly to the accepting sink.
      6. Build new automaton and test spot.are_equivalent(original, new).
      7. If equivalent → return the pseudo-linear automaton for use by label(q).

    This version builds the automaton using Spot's API (no hardcoded HOA).
    It is still being refined for full generality.
    """
    from testing.fusion_heuristic import try_absorb_size2_nonaccepting_scc as _impl
    return _impl(aut)


def ltl_to_tgba(ltl_str):
    """Translate LTL → TGBA using the same settings as the reconstruction."""
    f = spot.formula(ltl_str)
    aut = f.translate("GeneralizedBuchi", "Small", "High")
    return aut, f


def reconstruct_ltl(aut):
    """
    Backward LTL reconstruction from a TGBA.

    Returns:
        (final_formula, state_formulas)

    The reconstruction uses explicit recursion with memoization.
    - `state_formula` acts as the memoization table.
    - A pre-pass marks any state belonging to a multi-state SCC as unsupported.
    - Before labeling, we run the "fusion test" heuristic: absorption of
      size-2 non-accepting SCCs into a pseudo-linear form (when the
      transformation preserves the language). This is the main way we
      currently recover formulas that would otherwise be rejected.
    - A visiting set + hard depth limit guarantees that recursion is finite.
    - When the automaton has zero acceptance sets (trivial acceptance),
      every transition is treated as carrying acceptance. This allows the
      existing rules to handle very-weak automata (e.g. those coming from W).
    """
    # --- Pre-pass: detect multi-state SCCs (our main structural limitation) ---
    si = spot.scc_info(aut)
    bad_states = set()
    for scc_idx in range(si.scc_count()):
        states = list(si.states_of(scc_idx))
        if len(states) > 1:
            for q in states:
                bad_states.add(q)

    # --- Heuristic: try to absorb size-2 non-accepting SCCs (fusion test) ---
    massaged = try_absorb_size2_nonaccepting_scc(aut)
    if massaged is not None:
        aut = massaged
        # Recompute SCC info on the massaged automaton
        si = spot.scc_info(aut)
        bad_states = set()
        for scc_idx in range(si.scc_count()):
            states = list(si.states_of(scc_idx))
            if len(states) > 1:
                for q in states:
                    bad_states.add(q)

    # --- Pragmatic normalization for trivial acceptance ---
    treat_all_transitions_as_accepting = (aut.acc().num_sets() == 0)

    state_formula = {}   # memoization: state id -> LTL string
    visiting = set()     # current recursion stack (for cycle detection)
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
            # Back-edge into the current recursion stack
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

            if treat_all_transitions_as_accepting:
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

        # --- Apply the reconstruction rules ---
        if not exit_terms and self_loops:
            # Pure self-loop state
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

    # Light syntactic cleanup + Spot simplification (only on real formulas)
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
# Minimal manual testing entry point
# =============================================================================
if __name__ == "__main__":
    test_cases = [
        "(p U q) & GF r",
        "FG a",
        "a U b",
        "G (p -> X p) & GF q",
    ]

    for original_str in test_cases:
        print("\n" + "=" * 80)
        aut, _ = ltl_to_tgba(original_str)
        recovered, per_state = reconstruct_ltl(aut)

        print(f"Original LTL : {original_str}")
        print(f"States       : {aut.num_states()}")
        print(f"Recovered    : {recovered}")

        if recovered.startswith("UNSUPPORTED"):
            print("Status       : UNSUPPORTED")
        else:
            orig_f = spot.formula(original_str)
            rec_f = spot.formula(recovered)
            eq = spot.are_equivalent(orig_f, rec_f)
            print(f"Equivalent?  : {eq}")


# =============================================================================
# Demonstration of the size-2 absorption heuristic (fusion test)
# =============================================================================
if __name__ == "__main__" and False:   # change to True to run the demo
    demo = "X(p1 | F(p1 & Xp1))"
    print("\n" + "=" * 80)
    print(f"DEMO: size-2 absorption heuristic on {demo}")
    f = spot.formula(demo)
    aut = f.translate("GeneralizedBuchi", "Small", "High")
    print(f"Original automaton has {aut.num_states()} states")

    massaged = try_absorb_size2_nonaccepting_scc(aut)
    if massaged is not None:
        recovered, per_state = reconstruct_ltl(massaged)
        print(f"After absorption + reconstruction: {recovered}")
        orig_f = spot.formula(demo)
        rec_f = spot.formula(recovered)
        print(f"Equivalent to original? {spot.are_equivalent(orig_f, rec_f)}")
    else:
        print("Absorption heuristic did not apply or failed.")
