"""
Shared pure helpers for backward LTL reconstruction.

Automaton preprocessing (downstream invariants), tN-fragment injection /
multi-state-SCC rejection, the full-suffix sub-automaton, and the technique
tag. Split out of `reconstruction.py` so the engine module stays focused on
`reconstruct_ltl`/`label`; these helpers are representation-agnostic (they
operate on the automaton, not on the formula form the engine builds).
"""

import spot
import buddy

from .invariants import compute_invariant_literals


def _compute_state_invariants(aut):
    """
    For every state q, compute the set of invariant literals that hold
    on all edges reachable from q (including q itself).

    This is a one-time precomputation. The result is a dict:
        state -> set of literal strings, e.g. { "p2", "!p0" }
    """
    n = aut.num_states()
    # Precompute adjacency for reachability
    outgoing = [[] for _ in range(n)]
    for s in range(n):
        for e in aut.out(s):
            outgoing[s].append(e.dst)

    # Memoized reachability: state -> set of reachable states (including self)
    reachable_cache = {}

    def get_reachable(q):
        if q in reachable_cache:
            return reachable_cache[q]
        visited = set()
        stack = [q]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            stack.extend(outgoing[cur])
        reachable_cache[q] = visited
        return visited

    state_invariants = {}
    d = aut.get_dict()

    for q in range(n):
        # Collect edges from all states reachable from q (including q itself)
        # so that invariants correctly reflect literals forced on every possible
        # future transition starting from this state.
        downstream_states = get_reachable(q)

        edge_bdds = []
        for s in downstream_states:
            for e in aut.out(s):
                edge_bdds.append(e.cond)

        if edge_bdds:
            invs = compute_invariant_literals(edge_bdds, aut)
        else:
            invs = set()

        state_invariants[q] = invs

    return state_invariants


def _apply_downstream_invariants(aut, state_invariants):
    """
    For each state q, existentially quantify (from its immediate outgoing
    edge conditions) all the variables that are known to be invariant
    downstream from q.

    Returns a (possibly new) automaton with the simplified labels.
    """
    if not any(state_invariants.values()):
        return aut

    d = aut.get_dict()
    aps = list(aut.ap())
    num_aps = len(aps)

    # Build mapping AP index -> actual Buddy variable used in this aut
    ap_to_bdd_var = {}
    for i, ap in enumerate(aps):
        # Reliable way: create tiny automaton mentioning only this AP
        lit_f = spot.formula(str(ap))
        tmp = lit_f.translate()
        for e in tmp.out(tmp.get_init_state_number()):
            cond = e.cond
            if cond != buddy.bddtrue and cond != buddy.bddfalse:
                ap_to_bdd_var[i] = buddy.bdd_var(cond)
                break
        else:
            ap_to_bdd_var[i] = i   # fallback

    # Precompute per-source quantification cube (positive literals of the vars to quantify)
    source_cubes = {}
    for q in range(aut.num_states()):
        lits = state_invariants.get(q, set())
        if not lits:
            source_cubes[q] = buddy.bddtrue
            continue

        vars_to_quant = set()
        for lit in lits:
            name = lit[1:] if lit.startswith("!") else lit
            for i, ap in enumerate(aps):
                if str(ap) == name:
                    vars_to_quant.add(ap_to_bdd_var[i])
                    break

        cube = buddy.bddtrue
        for v in vars_to_quant:
            cube = cube & buddy.bdd_ithvar(v)
        source_cubes[q] = cube

    # Build new automaton with quantified conditions on outgoing edges
    new_aut = spot.make_twa_graph(d)
    new_aut.set_acceptance(aut.acc())
    new_aut.copy_ap_of(aut)

    state_map = {s: new_aut.new_state() for s in range(aut.num_states())}

    for src in range(aut.num_states()):
        cube = source_cubes[src]
        for e in aut.out(src):
            old_cond = e.cond
            if cube != buddy.bddtrue:
                new_cond = buddy.bdd_exist(old_cond, cube)
            else:
                new_cond = old_cond
            new_aut.new_edge(state_map[src], state_map[e.dst], new_cond, e.acc)

    new_aut.set_init_state(state_map[aut.get_init_state_number()])
    return new_aut


def _inject_tn_fragments_and_compute_bad_states(aut, scc_fragments, state_formula, absorbed):
    """Inject any pre-validated tN (terminal SCC) fragments and compute the
    set of "bad" (multi-state SCC) states that the labeler should immediately
    reject with UNSUPPORTED.

    This was extracted from the middle of reconstruct_ltl so the main
    orchestrator function is shorter and each phase has a name + docstring.
    The logic itself is unchanged.
    """
    # ------------------------------------------------------------------
    # Inject validated tN fragments into the global state_formula cache
    # *before* we run the multi-state-SCC rejection pass.
    # This is the key that lets the SCC states escape the "bad_states"
    # treatment that would otherwise nuke any |SCC|>1 component.
    # ------------------------------------------------------------------
    for st, frag in scc_fragments.items():
        state_formula[st] = frag

    # --- Structural safety filter (multi-state SCC rejection) ---
    # Any state that belongs to a non-trivial SCC and does *not* already have
    # a formula (from tN, from f2 absorption, or from a previous successful
    # recursion) is marked bad.  The label() function will immediately return
    # UNSUPPORTED for them.
    #
    # Because we pre-populated the tN states above, the test
    #     if q not in state_formula
    # protects exactly those states (and any f2-absorbed ones).
    si = spot.scc_info(aut)
    bad_states = set()
    if not absorbed:
        for scc_idx in range(si.scc_count()):
            states = list(si.states_of(scc_idx))
            if len(states) > 1:
                for q in states:
                    if q not in state_formula:
                        bad_states.add(q)

    # Belt-and-suspenders: even if something went wrong above, never let a
    # state that already carries a validated fragment be considered bad.
    bad_states -= set(state_formula.keys())
    return bad_states, state_formula


def _sub_automaton_from(aut, q):
    """The sub-automaton reachable from state q with q as the initial state —
    the unit of FULL-SUFFIX delegation. L(sub) is exactly the language sl's
    label(q) represents (sl walks the same automaton from q), so a label
    obtained for `sub` from any sound translator is interchangeable with sl's
    own label(q)."""
    sub = spot.automaton(aut.to_str("hoa"))
    sub.set_init_state(q)
    sub.purge_unreachable_states()
    return sub


def _compute_technique(absorbed, nice_terminal_sccs):
    """Build the human-readable technique tag (e.g. "sl+t2+t3+f2").

    Extracted so the end of reconstruct_ltl stays short and focused on
    "what do we return?" rather than "how do we name what we did?".
    The long comment explaining the tN naming convention lives with the
    implementation.
    """
    # ------------------------------------------------------------------
    # Technique string now reflects all heuristics that fired.
    # Historical values: "sl", "sl+f2"
    # tN generalized: we emit "tN" for each distinct size N of validated
    # terminal SCC(s) captured by the (now size-agnostic) nice-L-label rule.
    # Examples: "sl+t2", "sl+t3", "sl+t2+t3", "sl+f2+t4", ...
    # This makes larger SCC captures visible ("t3 or better") and searchable.
    # The order is deliberately f2 before the t* tags only because f2
    # rewrites the automaton before the terminal-SCC pass runs.
    # ------------------------------------------------------------------
    technique_parts = ["sl"]
    if absorbed:
        technique_parts.append("f2")
    if nice_terminal_sccs:
        sizes = sorted({len(info["states"]) for info in nice_terminal_sccs})
        for sz in sizes:
            technique_parts.append(f"t{sz}")
    return "+".join(technique_parts)
