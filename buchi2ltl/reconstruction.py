"""
Core backward LTL reconstruction logic.

This module contains the main `reconstruct_ltl` function and its internal
recursive labeling (`label`).

It is kept separate from heuristics and from calling / CLI code.
"""

import spot

from .heuristics.size2_overapprox import try_size2_overapprox


def reconstruct_ltl(aut):
    """
    Backward LTL reconstruction from a TGBA.

    The function first tries the size-2 absorption heuristic (fusion test).
    If that produces a language-equivalent pseudo-linear automaton, the
    rest of the reconstruction runs on the massaged automaton.

    Returns:
        (final_formula, state_formulas, technique)

    `technique` is a string describing which methods were used:
        - "sl"   : basic self-loop / semi-linear backward labeling
        - "sl+f2": the above + successful size-2 fusion/absorption ("f2")
    """
    # --- Heuristic layer: try to absorb size-2 non-accepting SCCs ---
    massaged = try_size2_overapprox(aut)
    absorbed = False
    if massaged is not None:
        aut = massaged
        absorbed = True   # trust the heuristic: do not re-apply the strict multi-state filter

    # --- Structural safety filter (skip if we just did absorption) ---
    si = spot.scc_info(aut)
    bad_states = set()
    if not absorbed:
        for scc_idx in range(si.scc_count()):
            states = list(si.states_of(scc_idx))
            if len(states) > 1:
                for q in states:
                    bad_states.add(q)

    # --- Trivial acceptance normalization ---
    treat_all_as_accepting = (aut.acc().num_sets() == 0)

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

        # Apply reconstruction rules
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

    technique = "sl+f2" if absorbed else "sl"
    return final, state_formula, technique
