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

# Enable detailed tracing only when RECONSTRUCT_TRACE=1
TRACE = os.environ.get("RECONSTRUCT_TRACE") == "1"


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

    # ------------------------------------------------------------------
    # NEW: Terminal 2-state SCC labeling heuristic ("t2")
    # ------------------------------------------------------------------
    # We attempt this *before* the structural safety filter that rejects any
    # SCC with more than one state.  The idea (exactly analogous to f2):
    #   - detect a very specific, very common shape (terminal 2-state SCC
    #     with nice L labels)
    #   - validate it in isolation via language equivalence
    #   - pre-declare the two states "good" by injecting a pre-validated
    #     formula fragment into the state_formula cache
    #   - teach the rest of the labeler to use that fragment instead of
    #     walking the cycle (which would blow up or produce horrible U/GF
    #     terms)
    #
    # Only SCCs that survive try_terminal_2scc_with_validation() (i.e. the
    # round-trip equivalence check inside the heuristic) are considered here.
    # ------------------------------------------------------------------
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
        print(f"[TRACE] t2: found {len(nice_terminal_sccs)} nice terminal 2-state SCC(s)")
        for info in nice_terminal_sccs:
            print(f"[TRACE]   SCC states: {info['states']}")
            print(f"[TRACE]     L = {info['L']}")
            print(f"[TRACE]     O = {info['O']}")
            print(f"[TRACE]     fragment = {info.get('validated_formula') or info.get('simplified')}")

    # --- Trivial acceptance normalization ---
    treat_all_as_accepting = (aut.acc().num_sets() == 0)

    state_formula = {}
    visiting = set()

    # ------------------------------------------------------------------
    # Inject validated t2 fragments into the global state_formula cache
    # *before* we run the multi-state-SCC rejection pass.
    # This is the key that lets the two SCC states escape the "bad_states"
    # treatment that would otherwise nuke any |SCC|>1 component.
    # ------------------------------------------------------------------
    for st, frag in scc_fragments.items():
        state_formula[st] = frag

    # --- Structural safety filter (multi-state SCC rejection) ---
    # Any state that belongs to a non-trivial SCC and does *not* already have
    # a formula (from t2, from f2 absorption, or from a previous successful
    # recursion) is marked bad.  The label() function will immediately return
    # UNSUPPORTED for them.
    #
    # Because we pre-populated the t2 states above, the test
    #     if q not in state_formula
    # protects exactly those two states (and any f2-absorbed ones).
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
        # t2 short-circuit #2 (the primary one for the two SCC states):
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
                # ------------------------------------------------------------------
                # t2-aware successor handling (the most subtle part of the integration)
                # ------------------------------------------------------------------
                # When we have a validated terminal 2-state SCC downstream we want:
                #   * states that merely exit *into* the SCC to build a clean
                #     "cond & X(fragment)" term (the user's stated expectation)
                #   * never to mark such a state UNSUPPORTED just because it has
                #     one edge into a still-unlabeled part of a larger SCC
                #
                # The logic below implements a "lenient" rule only when at least
                # one successor leads to a known-good t2 fragment.
                # ------------------------------------------------------------------

                # Fast pre-check: does this state have *any* edge that we already
                # know leads into a t2 fragment or a state that already has a formula?
                has_good_t2_successor = any(
                    (e2.dst in scc_fragments or e2.dst in state_formula)
                    for e2 in aut.out(q)
                )

                if e.dst in bad_states and e.dst not in state_formula and e.dst not in scc_fragments:
                    if has_good_t2_successor:
                        continue   # skip the bad edge; we have at least one good t2 branch
                    else:
                        state_formula[q] = UNSUPPORTED
                        visiting.remove(q)
                        depth[0] -= 1
                        return UNSUPPORTED

                # The heart of "use the precomputed fragment for the whole SCC":
                # If the immediate successor *is* one of the two SCC states, or if
                # any of its own successors is, we short-circuit the recursion and
                # just grab the validated G(...) string.  This prevents the labeler
                # from ever walking the internal cycle of the SCC.
                #
                # NEW (entry timing subtlety): when the edge is a *direct* crossing
                # into a t2 SCC state, we check whether its label L logically
                # implies the target's I(s) label (the steady-state "entry condition"
                # computed from internal incoming edges).  If yes, the invariant f
                # already holds on this letter, so we attach synchronously:
                #     (cond) & f          instead of the usual delayed (cond) & X(f)
                # This is what distinguishes "r U f" (second HOA) from "r & X f"
                # (first HOA) even though they share the same core 2-SCC f.
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
                        # Even after the lenient "has_good_t2_successor" test we may
                        # still land here for an edge that truly has no good future.
                        # Only declare the whole state bad if *none* of the other
                        # edges from q lead to a t2 fragment.
                        if not any((e2.dst in scc_fragments or e2.dst in state_formula)
                                   for e2 in aut.out(q) if e2.dst != e.dst):
                            state_formula[q] = UNSUPPORTED
                            visiting.remove(q)
                            depth[0] -= 1
                            return UNSUPPORTED
                        else:
                            # This particular edge is bad but we have other good
                            # t2 branches; just ignore it for the disjunction.
                            continue

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

                if cond == "1":
                    if direct_scc_sync_attach:
                        exit_terms.append(f"({succ_phi})")
                    else:
                        exit_terms.append(f"X({succ_phi})")
                else:
                    if direct_scc_sync_attach:
                        exit_terms.append(f"({cond}) & ({succ_phi})")
                    else:
                        exit_terms.append(f"({cond}) & X({succ_phi})")

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

    # ------------------------------------------------------------------
    # Technique string now reflects all heuristics that fired.
    # Historical values: "sl", "sl+f2"
    # New values seen in this work: "sl+t2", "sl+f2+t2"
    # The order is deliberately f2 before t2 only because f2 (absorption)
    # rewrites the automaton before t2 runs; the presence of either is
    # what matters for regression / evaluation.
    # ------------------------------------------------------------------
    technique_parts = ["sl"]
    if absorbed:
        technique_parts.append("f2")
    if nice_terminal_sccs:
        technique_parts.append("t2")
    technique = "+".join(technique_parts)
    return final, state_formula, technique
