"""
Core backward LTL reconstruction logic.

This module contains the main `reconstruct_ltl` function and its internal
recursive labeling (`label`).

It is kept separate from heuristics and from calling / CLI code.
"""

import os
import spot
import buddy

# The two heuristics that can "rescue" certain multi-state SCCs before we
# give up and emit UNSUPPORTED.  Both are tried (and validated) early.
from .heuristics.size2_overapprox import try_size2_overapprox
from .heuristics.terminal_2scc import try_terminal_2scc_with_validation
from .invariants import compute_invariant_literals

# Enable detailed tracing only when RECONSTRUCT_TRACE=1
TRACE = os.environ.get("RECONSTRUCT_TRACE") == "1"


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


def reconstruct_ltl(aut, scc_labeler=None):
    """
    Backward LTL reconstruction from a TGBA.

    The function first tries the size-2 absorption heuristic (fusion test).
    If that produces a language-equivalent pseudo-linear automaton, the
    rest of the reconstruction runs on the massaged automaton.

    `scc_labeler` (optional, default None — unchanged behavior): a callback
    `sub_automaton -> ltl_string_or_None`. When sl reaches a state q it cannot
    translate exactly (a multi-state SCC -> normally `UNSUPPORTED`), it instead
    delegates the whole sub-automaton from q (`_sub_automaton_from`) to this
    callback; a returned formula is spliced in as label(q) and the normal
    backward labeling continues around it (it is X-wrapped at the crossing edge,
    like any successor). This is the "kr under sl" seam: sl handles the very-weak
    envelope exactly, the callback (kr) handles the multi-cyclic core — on a
    SMALLER automaton than the whole. Sound when the callback is sound (the
    delegated label plays the exact role of sl's own label(q)). If the callback
    returns None, sl falls back to its usual `UNSUPPORTED`.

    Returns:
        (final_formula, state_formulas, technique)

    `technique` is a string describing which methods were used:
        - "sl"   : basic self-loop / semi-linear backward labeling
        - "sl+f2": the above + successful size-2 fusion/absorption ("f2")
    """

    # --- Heuristic layer: try to absorb size-2 non-accepting SCCs ---
    if TRACE:
        # Save using Spot's own DOT output *before* f2, so state numbers
        # exactly match everything printed in the [F2] traces.
        base = "trace_aut_before_f2"
        dotfile = base + ".dot"
        with open(dotfile, "w", encoding="utf-8") as f:
            f.write(aut.to_str("dot"))
        print(f"[TRACE] Saved automaton before f2 (over-approx) → {dotfile}")
        try:
            import subprocess, shutil
            if shutil.which("dot"):
                pngfile = base + ".png"
                subprocess.run(["dot", "-Tpng", "-o", pngfile, dotfile],
                               check=False, capture_output=True)
                print(f"[TRACE] Also rendered {pngfile}")
        except Exception:
            pass

    massaged = try_size2_overapprox(aut)
    absorbed = False
    if massaged is not None:
        aut = massaged
        absorbed = True   # trust the heuristic: do not re-apply the strict multi-state filter

        if TRACE:
            # Save after successful f2 rewrite (this is the automaton that will
            # be passed to t2 and the rest of the labeling).
            base = "trace_aut_after_f2"
            dotfile = base + ".dot"
            with open(dotfile, "w", encoding="utf-8") as f:
                f.write(aut.to_str("dot"))
            print(f"[TRACE] Saved automaton AFTER f2 over-approx → {dotfile}")
            try:
                import subprocess, shutil
                if shutil.which("dot"):
                    pngfile = base + ".png"
                    subprocess.run(["dot", "-Tpng", "-o", pngfile, dotfile],
                                   check=False, capture_output=True)
                    print(f"[TRACE] Also rendered {pngfile}  (use this + before_f2 to see exactly what the over-approx changed)")
            except Exception:
                pass

    # --- Precompute downstream invariants for every state (once, up front) ---
    # Literal sets (for simplification / quantification)
    state_invariant_literals = _compute_state_invariants(aut)

    # G-formula annotation (the main one we store "next to the formula label")
    state_invariants = {}
    for q, lits in state_invariant_literals.items():
        if lits:
            inv_inner = " & ".join(sorted(lits))
            state_invariants[q] = f"G({inv_inner})"
        else:
            state_invariants[q] = ""

    if TRACE:
        print("[TRACE] Downstream invariants per state (G-formulas, computed once):")
        for s in sorted(state_invariants):
            inv = state_invariants[s]
            if inv:
                print(f"  state {s}: {inv}")

    # --- Simplify outgoing edge labels by existentially quantifying downstream invariants ---
    aut = _apply_downstream_invariants(aut, state_invariant_literals)
    if TRACE and any(state_invariant_literals.values()):
        print("[TRACE] Applied existential quantification of downstream invariants on outgoing edges.")

    # ------------------------------------------------------------------
    # NEW: Terminal SCC labeling heuristic ("t2") - generalized beyond 2 states
    # ------------------------------------------------------------------
    # We attempt this *before* the structural safety filter that rejects any
    # SCC with more than one state.  The idea (exactly analogous to f2):
    #   - detect terminal SCCs that have per-state L labels which are pairwise
    #     mutually exclusive and all strictly tighter than true
    #   - validate the resulting G(OR (L(s) & X O(s))) fragment in isolation
    #     via language equivalence
    #   - pre-declare the SCC states "good" by injecting a pre-validated
    #     formula fragment into the state_formula cache
    #   - teach the rest of the labeler to use that fragment instead of
    #     walking the cycle (which would blow up or produce horrible U/GF
    #     terms)
    #
    # Only SCCs that survive try_terminal_2scc_with_validation() (i.e. the
    # round-trip equivalence check inside the heuristic) are considered here.
    # ------------------------------------------------------------------

    if TRACE:
        # Use Spot's native DOT output so the state numbers exactly match what
        # appears in all the [T2] / [TRACE] messages (e.g. states=[4, 6, 2] after f2).
        # This is the automaton handed to t2 (post-f2 if any).
        base = "trace_aut_before_t2"
        dotfile = base + ".dot"
        with open(dotfile, "w", encoding="utf-8") as f:
            f.write(aut.to_str("dot"))
        print(f"[TRACE] Saved automaton (exact current numbering) before t2 → {dotfile}")
        # Try to render PNG via graphviz 'dot' if available (best effort, silent on failure)
        try:
            import subprocess, shutil
            if shutil.which("dot"):
                pngfile = base + ".png"
                subprocess.run(["dot", "-Tpng", "-o", pngfile, dotfile],
                               check=False, capture_output=True)
                print(f"[TRACE] Also rendered {pngfile} (open to see states with the numbers used in traces)")
        except Exception:
            pass

    nice_terminal_sccs = try_terminal_2scc_with_validation(aut)
    nice_scc_states = set()
    scc_fragments = {}   # state -> validated formula fragment for its SCC
    scc_entry_I = {}     # state -> BDD of I(s): entry letters into this SCC state must imply it
    for info in nice_terminal_sccs:
        validated = info.get("validated_formula") or info.get("simplified")
        if validated:
            for st in info["states"]:
                nice_scc_states.add(st)
                scc_fragments[st] = validated
                if "L_bdd" in info and st in info["L_bdd"]:
                    scc_entry_I[st] = info["L_bdd"][st]

    if TRACE:
        sizes = [len(info["states"]) for info in nice_terminal_sccs]
        print(f"[TRACE] t*: found {len(nice_terminal_sccs)} nice terminal SCC(s), sizes={sizes}")
        for info in nice_terminal_sccs:
            print(f"[TRACE]   SCC states: {info['states']}")
            print(f"[TRACE]     L = {info['L']}")
            print(f"[TRACE]     O = {info['O']}")
            print(f"[TRACE]     fragment = {info.get('validated_formula') or info.get('simplified')}")

    if TRACE:
        # t2 never mutates the automaton (it only returns validated formula fragments).
        # Saving again gives you an "after t2" file with the exact same numbering
        # that the traces used.
        base = "trace_aut_after_t2"
        dotfile = base + ".dot"
        with open(dotfile, "w", encoding="utf-8") as f:
            f.write(aut.to_str("dot"))
        print(f"[TRACE] Saved automaton after t2 processing → {dotfile}")
        try:
            import subprocess, shutil
            if shutil.which("dot"):
                pngfile = base + ".png"
                subprocess.run(["dot", "-Tpng", "-o", pngfile, dotfile],
                               check=False, capture_output=True)
                print(f"[TRACE] Also rendered {pngfile}")
        except Exception:
            pass

    # --- Trivial acceptance normalization ---
    treat_all_as_accepting = (aut.acc().num_sets() == 0)

    # The heavy recursive labeling (the "label" closure + its 390 lines of
    # self-loop/exit/tN/short-circuit logic) remains here for now because it
    # is tightly coupled to many locals.  In a future pass we can move the
    # whole labeling service to buchi2ltl/labeling.py (one focused module)
    # the same way we extracted the GAP parser.
    state_formula = {}
    visiting = set()

    bad_states, state_formula = _inject_tn_fragments_and_compute_bad_states(
        aut, scc_fragments, state_formula, absorbed
    )

    # States in a multi-state SCC (>=2 states) are sl's hard cases — whether the
    # SCC is bottom or transient. With an scc_labeler set we delegate the whole
    # sub-automaton from such a state (full-suffix delegation) at label() entry,
    # which also pre-empts the `visiting` decline path that transient SCCs hit.
    _multi_scc_states = set()
    if scc_labeler is not None:
        _si = spot.scc_info(aut)
        for _s in range(_si.scc_count()):
            _members = _si.states_of(_s)
            if len(_members) >= 2:
                _multi_scc_states.update(int(x) for x in _members)

    MAX_DEPTH = 10000
    depth = [0]
    UNSUPPORTED = "UNSUPPORTED: non-trivial cycle or complex SCC"

    def _is_unsupported(val):
        """Return True if val is the clean unsupported sentinel (or contains it as a substring).
        This is our main defense against the sentinel leaking into constructed LTL strings.
        """
        if isinstance(val, str):
            return val.startswith("UNSUPPORTED") or "UNSUPPORTED" in val
        return False

    def label(q):
        if q in state_formula:
            return state_formula[q]

        # Full-suffix delegation (kr under sl), at the label point: if q is in a
        # multi-state SCC (sl's hard case, bottom OR transient), hand the whole
        # sub-automaton from q to the external labeler and splice the result as
        # label(q); the caller X-wraps it like any successor. Entry placement
        # pre-empts both the bad_states and the `visiting` decline paths. A None
        # result falls through to sl's usual handling (-> UNSUPPORTED).
        if scc_labeler is not None and q in _multi_scc_states:
            try:
                frag = scc_labeler(_sub_automaton_from(aut, q))
            except Exception:
                frag = None
            if frag:
                state_formula[q] = f"({frag})"
                return state_formula[q]

        if q in bad_states:
            state_formula[q] = UNSUPPORTED
            return UNSUPPORTED

        # ------------------------------------------------------------------
        # t2 short-circuit #1: the state already carries a pre-validated
        # fragment (either because we pre-populated it at the top of
        # reconstruct_ltl, or because an earlier recursive call stored it).
        # ------------------------------------------------------------------
        if q in state_formula:
            return state_formula[q]

        # ------------------------------------------------------------------
        # t2 short-circuit #2 (the primary one for SCC states):
        # We have a validated G(...) fragment for exactly this state.
        # Emit it immediately and do *not* walk the self-loops / exit edges
        # of the SCC.  Walking them would re-discover the cycle and produce
        # the horrible nested U/GF terms the user complained about.
        # ------------------------------------------------------------------
        if q in scc_fragments:
            if TRACE:
                print(f"[TRACE] label({q}): short-circuit with t2 fragment")
            phi = scc_fragments[q]
            state_formula[q] = phi
            return phi

        if q in visiting:
            state_formula[q] = UNSUPPORTED
            return UNSUPPORTED

        if depth[0] > MAX_DEPTH:
            state_formula[q] = UNSUPPORTED
            return UNSUPPORTED

        visiting.add(q)
        depth[0] += 1

        current_inv = state_invariants.get(q, "")

        self_loops = []
        exit_terms = []

        for e in aut.out(q):
            cond = spot.bdd_format_formula(aut.get_dict(), e.cond)

            if treat_all_as_accepting:
                # No real acceptance sets (vacuously accepting)
                acc_sets = frozenset()
            else:
                acc_sets = frozenset(e.acc.sets())

            if e.src == e.dst:
                self_loops.append((cond, acc_sets))
            else:
                # ------------------------------------------------------------------
                # t2-aware successor handling (the most subtle part of the integration)
                # ------------------------------------------------------------------
                # Core principle (per user specification):
                #   The sync-vs-delay decision is made *per transition* on the
                #   specific edge whose label actually lands inside the t2 SCC.
                #
                #   - For each individual crossing edge with label L into target s:
                #       if L implies I(s)  → attach synchronously:  (L) & f
                #       else               → attach with one-step shift: (L) & X(f)
                #
                #   Multiple arcs from the same state into the SCC are handled
                #   independently; their terms are OR-ed in the normal way.
                #
                # When a validated terminal SCC (t2) is downstream we also want:
                #   * never to mark a state UNSUPPORTED just because it has one
                #     edge into a still-unlabeled part of a larger SCC (lenient rule
                #     only when at least one successor leads to a known-good t2 fragment).
                # ------------------------------------------------------------------

                if (e.dst in bad_states and e.dst not in state_formula
                        and e.dst not in scc_fragments and scc_labeler is None):
                    # Strict hardening: we have no reconstruction algorithm for
                    # states inside this multi-state SCC. Silently dropping the
                    # branch (as was done for t2 leniency) can produce wrong
                    # but plausible formulas. Instead, the whole current state
                    # must be UNSUPPORTED. (With an scc_labeler we instead fall
                    # through so label(e.dst) can delegate the sub-automaton.)
                    if TRACE:
                        print(f"[TRACE] label({q}): encountered bad successor {e.dst} with no fragment -> UNSUPPORTED")
                    state_formula[q] = UNSUPPORTED
                    visiting.remove(q)
                    depth[0] -= 1
                    return UNSUPPORTED

                # The heart of "use the precomputed fragment for the whole SCC":
                # If the immediate successor *is* one of the SCC states (any size),
                # or if any of its own successors is, we short-circuit the recursion
                # and just grab the validated G(...) string.  This prevents the labeler
                # from ever walking the internal cycle of the SCC.
                #
                # Per-transition entry timing (the key subtlety):
                # When the edge from the current state is a *direct* crossing into
                # a t2 SCC state, we perform a cheap BDD implication test:
                #     does the edge label L logically imply the target's I(s)?
                # (I(s) = the steady-state "state label" computed by the t2 heuristic
                #  from internal incoming edges of the SCC.)
                #
                # If yes → the invariant already holds on this letter → synchronous
                #     (cond) & f
                # Else  → delayed
                #     (cond) & X(f)
                #
                # This rule is applied independently to every direct crossing edge.
                # It is what distinguishes "r U f" from "r & X f" (and more complex
                # mixtures) even when they share the same core 2-SCC fragment.
                direct_scc_sync_attach = False
                if e.dst in scc_fragments:
                    succ_phi = scc_fragments[e.dst]
                    i_bdd = scc_entry_I.get(e.dst)
                    if i_bdd is not None:
                        crossing_bdd = e.cond
                        # L implies I(s)  <=>  no counterexample letter that is in L but not I
                        if (crossing_bdd & buddy.bdd_not(i_bdd)) == buddy.bddfalse:
                            direct_scc_sync_attach = True
                elif any(e2.dst in scc_fragments or e2.dst in state_formula for e2 in aut.out(e.dst)):
                    # The successor is an intermediate state that can reach a t2
                    # fragment in one step.  We must still call label() on it so that
                    # the *actual crossing edge(s)* from the intermediate into the SCC
                    # get the correct per-transition sync vs delayed decision
                    # (based on whether their label implies the target's I(s)).
                    #
                    # The old direct "grab grandchild fragment" short-circuit violated
                    # the principle that the X-or-not rule is specific to each
                    # transition that actually enters the SCC.
                    succ_phi = label(e.dst)
                else:
                    succ_phi = label(e.dst)
                    if isinstance(succ_phi, str) and succ_phi.startswith("UNSUPPORTED"):
                        # Strict hardening: if any successor we tried to label
                        # ended up unsupported (typically because it hit a bad
                        # multi-state SCC with no fragment), the whole current
                        # state is unsupported. We do not silently drop branches.
                        if TRACE:
                            print(f"[TRACE] label({q}): successor {e.dst} returned UNSUPPORTED -> whole state UNSUPPORTED")
                        state_formula[q] = UNSUPPORTED
                        visiting.remove(q)
                        depth[0] -= 1
                        return UNSUPPORTED

                # ------------------------------------------------------------------
                # HARD GUARD: Never allow the UNSUPPORTED sentinel to be wrapped
                # into a compound term like "(cond) & X(UNSUPPORTED...)".
                # If any successor formula is unsupported, the whole state is
                # unsupported. This is the main defense against polluted output.
                # ------------------------------------------------------------------
                if _is_unsupported(succ_phi):
                    state_formula[q] = UNSUPPORTED
                    visiting.remove(q)
                    depth[0] -= 1
                    return UNSUPPORTED

                # --- New connection rule: label of successor AND its downstream invariant ---
                target = e.dst
                inv_formula = state_invariants.get(target, "")

                if e.dst in scc_fragments:
                    # SCC case: always X the invariant part (which already contains its G).
                    # For the SCC labeling part, still use the old compatibility test
                    # (direct_scc_sync_attach) to decide sync vs X.
                    scc_part = succ_phi
                    if direct_scc_sync_attach:
                        scc_wrapped = f"({scc_part})"
                    else:
                        scc_wrapped = f"X({scc_part})"

                    if inv_formula:
                        term = f"({scc_wrapped}) & X({inv_formula})"
                    else:
                        term = scc_wrapped
                else:
                    # Normal (non-SCC) successor: label AND invariant (same timing)
                    base = succ_phi
                    if inv_formula:
                        term = f"({base}) & ({inv_formula})"
                    else:
                        term = base

                if current_inv:
                    if cond == "1":
                        edge_prefix = current_inv
                        if e.dst in scc_fragments:
                            exit_terms.append(f"({edge_prefix}) & ({term})")
                        else:
                            exit_terms.append(f"({edge_prefix}) & X({term})")
                    else:
                        edge_prefix = f"({cond}) & ({current_inv})"
                        if e.dst in scc_fragments:
                            exit_terms.append(f"({edge_prefix}) & ({term})")
                        else:
                            exit_terms.append(f"({edge_prefix}) & X({term})")
                else:
                    if e.dst in scc_fragments:
                        if cond == "1":
                            exit_terms.append(f"({term})")
                        else:
                            exit_terms.append(f"({cond}) & ({term})")
                    else:
                        if cond == "1":
                            exit_terms.append(f"X({term})")
                        else:
                            exit_terms.append(f"({cond}) & X({term})")

        # (debug prints for this session removed)

        # ------------------------------------------------------------------
        # Pre-construction safety: if any piece we are about to use in the
        # final formula is the unsupported sentinel, abort cleanly now.
        # ------------------------------------------------------------------
        all_pieces = [c for c, _ in self_loops] + exit_terms
        if any(_is_unsupported(p) for p in all_pieces):
            phi = UNSUPPORTED
            state_formula[q] = phi
            visiting.remove(q)
            depth[0] -= 1
            if TRACE:
                print(f"[TRACE] label({q}) assigned formula: {phi}")
            return phi

        # Apply reconstruction rules
        if not exit_terms and self_loops:
            or_all = " | ".join(f"({c})" for c, _ in self_loops)
            if len(self_loops) > 1:
                or_all = f"({or_all})"

            # Compute how many distinct acc sets are actually touched by self-loops of *this* state
            touched_sets = set()
            for _, acc in self_loops:
                touched_sets.update(acc)
            local_num_sets = len(touched_sets)

            if local_num_sets <= 1 or treat_all_as_accepting:
                # Legacy behavior (exact string compatibility for 0/1 acc set cases)
                acc_cs = [c for c, acc in self_loops if acc]
                if acc_cs:
                    or_acc = " | ".join(f"({c})" for c in acc_cs)
                    if len(acc_cs) > 1:
                        or_acc = f"({or_acc})"
                    phi = f"G({or_all}) & GF({or_acc})"
                else:
                    phi = f"G({or_all})"
            else:
                # Generalized Büchi: this state has self-loops touching 2+ acc sets.
                # Emit G(OR all) & GF(cover0) & GF(cover1) ...
                gfs = []
                for i in sorted(touched_sets):
                    covering = [c for c, acc in self_loops if i in acc]
                    if covering:
                        or_i = " | ".join(f"({c})" for c in covering)
                        if len(covering) > 1:
                            or_i = f"({or_i})"
                        gfs.append(f"GF({or_i})")
                if gfs:
                    phi = f"G({or_all}) & {' & '.join(gfs)}"
                else:
                    phi = f"G({or_all})"

            inv = state_invariants.get(q, "")
            if inv:
                phi = f"({phi}) & ({inv})"

        elif exit_terms:
            or_ex = " | ".join(exit_terms)
            if len(exit_terms) > 1:
                or_ex = f"({or_ex})"
            # Under trivial acceptance every self-loop is accepting (vacuously),
            # so treat it the same as a real acc set for the mixed-case decision.
            has_acc = any(acc for _, acc in self_loops) or (treat_all_as_accepting and bool(self_loops))

            if has_acc:
                # --- Generalized Büchi handling for the mixed (has-exits) case ---
                # Previously this was always the legacy single-GF(or of any accepting self-loop).
                # That was insufficient for >1 acc sets when self-loops carry partial marks
                # (e.g. one loop only Inf(0), one only Inf(1), one both, one none).
                # The correct "stay forever" must ensure each required Inf set is covered i.o.
                # We now mirror the logic from the pure-self-loop case above.
                #
                # touched_sets = union of acc sets touched by *this state's* self-loops only.
                # For each such set i we compute the disjunction of conds that provide i.
                # This produces the proper G(OR all self conds) & GF(cover_for_0) & GF(cover_for_1) ...
                # for the "stay" branch, while still allowing the (or_self U exit) "leave" option.
                touched_sets = set()
                for _, acc in self_loops:
                    touched_sets.update(acc)
                local_num_sets = len(touched_sets)

                or_self = " | ".join(f"({c})" for c, _ in self_loops)
                if len(self_loops) > 1:
                    or_self = f"({or_self})"

                if local_num_sets <= 1 or treat_all_as_accepting:
                    # Legacy behavior (exact string compatibility for 0/1 acc set cases)
                    acc_cs = [c for c, acc in self_loops if acc]
                    or_acc = " | ".join(f"({c})" for c in acc_cs) if acc_cs else "true"
                    if len(acc_cs) > 1:
                        or_acc = f"({or_acc})"
                    stay = f"G({or_self}) & GF({or_acc})"
                else:
                    # Generalized Büchi (multi acc sets): build per-set covering GFs
                    gfs = []
                    for i in sorted(touched_sets):
                        covering = [c for c, acc in self_loops if i in acc]
                        if covering:
                            or_i = " | ".join(f"({c})" for c in covering)
                            if len(covering) > 1:
                                or_i = f"({or_i})"
                            gfs.append(f"GF({or_i})")
                    stay = f"G({or_self}) & {' & '.join(gfs)}" if gfs else f"G({or_self})"

                inv = state_invariants.get(q, "")
                if inv:
                    stay = f"({stay}) & ({inv})"
                or_self_u = f"(({or_self}) & ({inv}))" if inv else or_self
                phi = f"({stay}) | ({or_self_u} U ({or_ex}))"
            else:
                if self_loops:
                    or_self = " | ".join(f"({c})" for c, _ in self_loops)
                    if len(self_loops) > 1:
                        or_self = f"({or_self})"
                    inv = state_invariants.get(q, "")
                    if inv:
                        or_self = f"({or_self}) & ({inv})"
                    phi = f"({or_self}) U ({or_ex})"
                else:
                    phi = or_ex
        else:
            phi = "false"

        # ------------------------------------------------------------------
        # Final belt-and-suspenders: if for any reason a constructed phi
        # contains the sentinel (from self-loops, complex U/GF cases, etc.),
        # force the clean sentinel. We must NEVER return a string containing
        # "UNSUPPORTED" to the caller as if it were a valid LTL formula.
        # ------------------------------------------------------------------
        if _is_unsupported(phi):
            phi = UNSUPPORTED

        state_formula[q] = phi
        visiting.remove(q)
        depth[0] -= 1
        if TRACE:
            print(f"[TRACE] label({q}) assigned formula: {phi}")
        return phi

    init = aut.get_init_state_number()
    final = label(init)

    if not (isinstance(final, str) and final.startswith("UNSUPPORTED")):
        final = final.replace(" & X(true)", " X true")
        final = final.replace("X(true)", "X true")
        final = final.replace("G(true)", "G true")
        final = final.replace("G(1)", "G true")

        # DEBUG MODE: Do NOT call Spot simplification.
        # The user explicitly requested to keep formulas raw during debugging
        # because Spot rewriting (especially to W, etc.) hides the structure
        # actually built by the reconstruction rules.
        #
        # try:
        #     final = str(spot.formula(final).simplify())
        # except Exception:
        #     pass
        #
        # For now we leave the raw constructed string (after only the trivial replacements above).

    technique = _compute_technique(absorbed, nice_terminal_sccs)
    return final, state_formula, technique


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
