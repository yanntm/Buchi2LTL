"""
Generic computation of invariant literals across a set of BDD formulas.

This is developed separately from the main t2 heuristic and reconstruction
for now, as requested.

An atom p is an *invariant* (constantly true or constantly false) for a
set of formulas {φ1, ..., φn} if all the formulas agree on its value:

- p is constantly true if  ∀i.  φi ⊨ p     (i.e. φi ∧ ¬p is unsatisfiable for all i)
- p is constantly false if ∀i.  φi ⊨ ¬p

We return the set of literals (as strings, e.g. "p2" or "!p0") that are
forced by the entire set.
"""

import spot
import buddy


def _get_ap_var_mapping(aut):
    """
    Return two mappings:
        ap_index_to_name : {0: "p0", 1: "p1", ...}
        ap_index_to_bdd_var : {0: 2, 1: 4, ...}   # actual Buddy variable for that AP
    """
    d = aut.get_dict()
    aps = list(aut.ap())
    ap_index_to_name = {}
    ap_index_to_bdd_var = {}

    for i, ap in enumerate(aps):
        ap_name = str(ap)
        ap_index_to_name[i] = ap_name

        # Create a tiny automaton that only mentions this AP, then read the variable
        # from one of its edge conditions. This is the most reliable way.
        lit_f = spot.formula(ap_name)
        tmp = lit_f.translate()
        for e in tmp.out(tmp.get_init_state_number()):
            cond = e.cond
            if cond != buddy.bddtrue and cond != buddy.bddfalse:
                v = buddy.bdd_var(cond)
                ap_index_to_bdd_var[i] = v
                break
        else:
            # Fallback (should not happen for real APs)
            ap_index_to_bdd_var[i] = i

    return ap_index_to_name, ap_index_to_bdd_var


def compute_invariant_literals(formulas, aut):
    """
    Given a list of BDDs (formulas) and the automaton they come from,
    return the set of literals that are invariant (forced true or forced false)
    across *all* the formulas.

    This is the generic BDD-based version:
        p is constantly true  iff  ∀ φi .  φi ⊨ p     (i.e. φi & ~p == false for all i)
        p is constantly false iff  ∀ φi .  φi ⊨ ¬p

    Parameters
    ----------
    formulas : list of buddy.BDD
        The set of formulas (typically the internal edge conditions of a terminal SCC).
    aut : spot.twa_graph
        The automaton (used to discover the correct Buddy variables for each AP).

    Returns
    -------
    set of str
        Literals that are constant across the whole set, e.g. {"p2", "!p0"}.
        Empty set if nothing is invariant.
    """
    if not formulas:
        return set()

    d = aut.get_dict()
    ap_index_to_name, ap_index_to_bdd_var = _get_ap_var_mapping(aut)

    invariants = set()

    for i, ap_name in ap_index_to_name.items():
        v = ap_index_to_bdd_var[i]
        p_bdd = buddy.bdd_ithvar(v)
        not_p = buddy.bdd_not(p_bdd)

        # p is constantly true?
        always_true = True
        for phi in formulas:
            if (phi & not_p) != buddy.bddfalse:
                always_true = False
                break

        if always_true:
            invariants.add(ap_name)
            continue

        # p is constantly false?
        always_false = True
        for phi in formulas:
            if (phi & p_bdd) != buddy.bddfalse:
                always_false = False
                break

        if always_false:
            invariants.add("!" + ap_name)

    return invariants


# ----------------------------------------------------------------------
# Small self-test / demonstration when run directly
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Reproduce the running example
    formula_str = "G(Xp2 & (p0 | Xp1))"
    f = spot.formula(formula_str)
    aut = f.translate("GeneralizedBuchi", "Small", "High")

    # Internal edge conditions of the terminal SCC {1,2}
    scc_states = [1, 2]
    internal = []
    d = aut.get_dict()
    for st in scc_states:
        for e in aut.out(st):
            if e.dst in scc_states:
                internal.append(e.cond)
                print("Internal:", spot.bdd_format_formula(d, e.cond))

    invs = compute_invariant_literals(internal, aut)
    print("\nInvariant literals:", sorted(invs))
    print("Expected: ['p2']")
