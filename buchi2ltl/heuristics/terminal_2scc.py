"""
Heuristic for "nice" terminal accepting SCCs (the "t2" pattern, generalized).

-------------------------------------------------------------------------------
MOTIVATION AND APPROACH
-------------------------------------------------------------------------------
Many LTL formulas that are "eventually linear" (after some prefix behavior they
settle into a simple oscillation) produce TGBA with a terminal SCC of any
size >=2 under the "GeneralizedBuchi Small High" translation from Spot.
The original implementation required exactly two states; this has been relaxed
to any size as long as the per-state L labels (derived from internal incoming
edges) are pairwise mutually exclusive and all strictly tighter than true.

Classic examples:
    G(p -> X q)          --> terminal SCC {0,1} with p-dependent choice of entry
    G((!p & X p) | (p & X !p))   (alternating)
    many GF(p & X q) variants after some prefix

For such SCCs the two states can be given *state labels* L derived purely from
the automaton structure:
    L(s) = OR of all (formulas on edges entering s)

If all L(s) for s in the SCC are:
    - strictly tighter than "true"  (i.e. they actually constrain the alphabet)
    - pairwise mutually exclusive (L(s) & L(t) == false for s != t)

then the whole SCC can be described by the single LTL formula

    G(  OR_{s in SCC} (L(s) & X O(s))  )

where O(s) is the OR of the conditions on edges *leaving* s.

This is a sound characterization of "being in the SCC forever".

-------------------------------------------------------------------------------
SOUNDNESS
-------------------------------------------------------------------------------
We never trust the pattern on faith.  try_terminal_2scc_with_validation()
isolates the SCC states + their *internal* transitions into a fresh automaton,
translates the candidate G(...) back to an automaton with the same settings,
and only accepts the fragment if spot.are_equivalent() holds.

Only after this round-trip check do we pre-populate state_formula[] in the
main reconstruction and protect the SCC states from the "bad_states" multi-SCC
rejection pass.

-------------------------------------------------------------------------------
KEY DESIGN DECISIONS (history)
-------------------------------------------------------------------------------
* We compute L using *only internal edges of the SCC* (see
  _compute_internal_incoming_or).  Using the whole automaton polluted L with
  literals from transient prefix states (e.g. an "r" that only appears on an
  edge leading into the SCC).  The user explicitly asked for the internal-only
  variant first.

* We dropped the "initial state rewiring / precursor split" for the production
  path (user: "Drop the whole precursor thing, we just accept it if initial
  state is one of the SCC").  The split code is preserved in
  testing/initial_state_rewiring.py for future experiments or debugging.

* No Spot simplification is performed on the produced fragment during
  reconstruction (see utils.py and the commented-out .simplify() here).  This
  keeps the raw G&X structure visible for debugging; W operators etc. hide the
  reconstruction decisions.

* We look for the pattern *before* the blanket |SCC|>1 rejection in
  reconstruction.py, exactly analogous to how size-2 fusion (f2) is tried.

-------------------------------------------------------------------------------
CURRENT LIMITATIONS / OPEN QUESTIONS
-------------------------------------------------------------------------------
The pattern gives a *steady-state* description of the SCC.  When a prefix leads
into it, the entry edge may choose which of the SCC states we land in first.
Some formulas (e.g. "r U G(!p | Xq)") have p-dependent choice of entry state.
The current symmetric G(...) can over-approximate the entry and produce a
slightly different automaton for the full formula.  The reconstruction layer
now resolves the exact entry-timing subtlety (see the two HOA examples with
"r & XG(!p | Xq)" vs "r U G(!p | Xq)"): when attaching a prefix to the SCC
fragment it checks (via BDD implication) whether each crossing label L implies
the I(s_in) of its target SCC state.  If yes the invariant is attached
synchronously as "(L) & f"; otherwise the delayed "(L) & X(f)" is used.
This yields the precise "r U f" vs "r & X f" shapes for the two cases.

The technique is therefore marked "t2" in the reported technique string and is
still considered experimental / in need of refining, but it already turns many
previously-UNSUPPORTED cases into fully supported, equivalence-checked ones.

See also:
- testing/initial_state_rewiring.py   (the discarded split + early experiments)
- testing/find_terminal_2scc_cases.py (how the stable sample set was produced)
- samples/terminal_2scc_labeled.py    (100 formulas where t2 activates)
"""

import spot

# ---------------------------------------------------------------------------
# NOTE ON INITIAL-STATE REWIRING
# ---------------------------------------------------------------------------
# The initial state split logic (making init a pure source node with only
# outgoing edges) has been dropped for the t2 path per explicit user request
# during debugging of r & X G(p->Xq) etc.:
#     "Drop the whole precursor thing, the initial precursor state thing.
#      We just accept it if initial state is one of the SCC."
#
# A complete implementation of split_initial_state() plus the before/after
# visualization helpers is kept in:
#     testing/initial_state_rewiring.py
#
# It is no longer called from reconstruction.py or from this module.
# We simply tolerate the case where the original initial state is one of the
# two SCC states.
# ---------------------------------------------------------------------------


def _compute_incoming_or(aut, state):
    """
    (Legacy / whole-automaton variant)
    Return (bdd, formula_str) for the disjunction of all edge conditions that
    have `state` as their destination, considering *every* transition in `aut`.

    This was the first version used during experiments.  It is kept for
    reference and potential future "quantify away external APs" variants.
    """
    d = aut.get_dict()
    conds = []
    for src in range(aut.num_states()):
        for e in aut.out(src):
            if e.dst == state:
                conds.append(e.cond)
    if not conds:
        return spot.bddfalse, "false"
    res = conds[0]
    for c in conds[1:]:
        res = res | c
    return res, spot.bdd_format_formula(d, res)


def _compute_internal_incoming_or(aut, state, scc_states):
    """
    Return (bdd, formula_str) for the OR of conditions on edges whose
    *source* is inside the given 2-state SCC and whose destination is `state`.

    This is the version used in production for the t2 heuristic.

    WHY ONLY INTERNAL EDGES?
    ------------------------
    When a transient prefix state has an edge into the SCC carrying a literal
    that never appears on any *internal* transition of the SCC (classic example:
    "r & X G(p -> X q)"), the whole-automaton version of L would contain that
    literal (e.g. L(0) = "r & !p").  That literal does not belong to the
    "steady-state" alphabet of the SCC; it is part of the *entry condition*
    from outside.

    Using only internal edges gives the pure steady-state labels that the
    G(L & X O || ...) pattern expects.  The prefix handling is left to the
    normal reconstruction rules on the states *before* the SCC (they will emit
    the appropriate "r & X(...)" wrapper using the fragment we pre-populate
    for the SCC states).

    The user explicitly chose this variant after seeing polluted labels on
    the "r & X ..." family.
    """
    d = aut.get_dict()
    conds = []
    for src in scc_states:
        for e in aut.out(src):
            if e.dst == state:
                conds.append(e.cond)
    if not conds:
        return spot.bddfalse, "false"
    res = conds[0]
    for c in conds[1:]:
        res = res | c
    return res, spot.bdd_format_formula(d, res)


def _compute_outgoing_or(aut, state):
    """
    Return (bdd, formula_str) for the OR of all conditions on transitions
    leaving `state`.  Used for the "O" part of the pattern.

    O(s) describes "what the automaton can do in the next step while staying
    inside the SCC", exactly what appears under the X in the generated G formula.
    """
    d = aut.get_dict()
    conds = [e.cond for e in aut.out(state)]
    if not conds:
        return None, "false"
    res = conds[0]
    for c in conds[1:]:
        res = res | c
    return res, spot.bdd_format_formula(d, res)


def find_nice_terminal_2sccs(aut):
    """
    Scan the automaton for terminal SCCs (of any size >=2) for which we can
    compute "nice" per-state labels L(s).

    A nice terminal SCC satisfies:
        1. Size >= 2.
        2. It is terminal: every outgoing transition from any state stays
           inside the SCC (no escape edges).
        3. Every L label (OR of *internal* incoming edges to that state) is
           strictly tighter than "true".
        4. All L labels are pairwise mutually exclusive: for every distinct
           pair s,t we have L(s) & L(t) == false.

    When all four hold we synthesize the candidate steady-state formula

        G( (L(s1) & X O(s1)) | (L(s2) & X O(s2)) | ... )

    This generalizes the original "t2" (terminal-2-state) rule. The user
    observed that the pairwise-disjointness of the L labels is what matters
    for a precise disjunctive characterization; the hard size==2 limit was
    unnecessary.

    The function deliberately does *not* call any initial-state rewiring.
    If the original initial state happens to be one of the SCC states we
    still accept the SCC (the main reconstruction will just use the fragment
    for that state directly).

    Returns a list of dicts (one per nice SCC found; usually 0 or 1).
    Each dict contains:
        states, L, L_bdd, O, formula, simplified
    """
    si = spot.scc_info(aut)
    results = []

    for scc in range(si.scc_count()):
        states = list(si.states_of(scc))
        if len(states) < 2:
            continue

        # Terminal check: every successor of every state in the SCC must
        # itself belong to the same SCC.
        is_terminal = all(si.scc_of(e.dst) == scc for st in states for e in aut.out(st))
        if not is_terminal:
            continue

        # ------------------------------------------------------------------
        # L(s) = "state label when you are in this state"
        #      = disjunction of all formulas on *internal* edges that enter s
        # We use the internal-only variant so that literals belonging only
        # to incoming edges from transient states do not pollute the label.
        # ------------------------------------------------------------------
        L_bdds = {}
        L_strs = {}
        all_tight = True
        for st in states:
            bdd, s = _compute_internal_incoming_or(aut, st, states)
            L_bdds[st] = bdd
            L_strs[st] = s
            if s in ("1", "true"):
                all_tight = False
        if not all_tight:
            continue

        # Pairwise mutual exclusion: the key property that lets us emit a
        # clean top-level disjunction under the outer G.  If any pair overlaps
        # we cannot use the pattern.
        mutually_exclusive = True
        d = aut.get_dict()
        for i in range(len(states)):
            for j in range(i + 1, len(states)):
                inter = L_bdds[states[i]] & L_bdds[states[j]]
                inter_str = spot.bdd_format_formula(d, inter)
                # simplify only for the boolean test
                if str(spot.formula(inter_str).simplify()) not in ("0", "false"):
                    mutually_exclusive = False
                    break
            if not mutually_exclusive:
                break
        if not mutually_exclusive:
            continue

        # O labels (allowed to be "true").
        O_strs = {}
        for st in states:
            _, o = _compute_outgoing_or(aut, st)
            O_strs[st] = o

        # Build the (generalized) raw pattern.
        terms = [f"({L_strs[st]} & X({O_strs[st]}))" for st in states]
        disj = " | ".join(terms)
        formula = f"G( ({disj}) )"

        # Keep raw (no Spot simplification).
        simplified = formula

        results.append({
            "states": states,
            "L": L_strs,
            "L_bdd": L_bdds,
            "O": O_strs,
            "formula": formula,
            "simplified": simplified,
        })

    return results


def try_terminal_2scc_heuristic(aut):
    """
    Lightweight entry point (analogous to try_size2_overapprox).

    Returns the raw list of *candidate* nice terminal SCC dicts (any size >=2)
    without performing the expensive language-equivalence validation.

    In the current integration we always go through the validating wrapper
    below, so this function is mainly useful for quick diagnostics or
    external tooling.
    """
    return find_nice_terminal_2sccs(aut)


def validate_terminal_2scc(aut, nice_info):
    """
    Soundness gate for a candidate t2 fragment (generalized to N-state SCCs).

    We build a *tiny isolated automaton* that contains *only* the SCC states
    and the internal transitions.  We then translate the candidate
    G( (L1 & X O1) | ... ) back to a TGBA with identical settings
    ("GeneralizedBuchi Small High") and ask Spot whether the two automata
    recognize exactly the same language.

    Only when spot.are_equivalent() returns True do we trust the fragment
    enough to inject it into the main reconstruction.

    This is the "sound via emptiness/equivalence checks on small isolated
    fragments" principle that the whole project follows.

    Parameters
    ----------
    aut : spot.twa_graph
        The original (possibly large) automaton.
    nice_info : dict
        One of the dicts returned by find_nice_terminal_2sccs.

    Returns
    -------
    str or None
        The validated (raw) formula string if the round-trip succeeds,
        otherwise None.  We deliberately return the *unsimplified* form
        so that the reconstruction can see the exact G&X shape it produced.
    """
    if not nice_info:
        return None

    states = nice_info["states"]
    candidate = nice_info.get("simplified") or nice_info.get("formula")
    if not candidate:
        return None

    # ------------------------------------------------------------------
    # Build the isolated SCC fragment (any size >=2).
    # We copy *only* transitions whose both ends are inside the SCC.
    # This gives us a pure "the automaton is now in this SCC forever"
    # sub-problem, independent of any prefix that may have led here.
    # No initial-state rewiring is applied (see module docstring).
    # ------------------------------------------------------------------
    small = spot.make_twa_graph(aut.get_dict())
    small.set_acceptance(aut.acc())
    small.copy_ap_of(aut)

    state_map = {st: small.new_state() for st in states}

    for st in states:
        for e in aut.out(st):
            if e.dst in states:   # keep only internal edges
                small.new_edge(state_map[st], state_map[e.dst], e.cond, e.acc)

    # The choice of which state we declare initial does not matter for
    # language equivalence of a strongly-connected component; the
    # are_equivalent check will explore the whole cycle anyway.
    small.set_init_state(state_map[states[0]])

    try:
        # Translate with the exact same options used everywhere else in the
        # project so that the comparison is apples-to-apples.
        cand_aut = spot.formula(candidate).translate("GeneralizedBuchi", "Small", "High")
        if spot.are_equivalent(small, cand_aut):
            # DEBUG MODE: return the raw candidate, never the simplified form.
            # (The commented line shows what a non-debug version would do.)
            return candidate
    except Exception:
        # Any translation or equivalence error -> treat as failure for this
        # candidate.  We stay silent here; the caller can log if needed.
        pass

    return None


# ---------------------------------------------------------------------------
# VALIDATING ENTRY POINT USED BY THE MAIN RECONSTRUCTION
# ---------------------------------------------------------------------------

def try_terminal_2scc_with_validation(aut):
    """
    The function actually called from reconstruction.reconstruct_ltl.

    Pipeline
    --------
    1. Run the syntactic / structural pattern matcher
       (find_nice_terminal_2sccs).  This is cheap.
    2. For every syntactic candidate, run the full soundness round-trip
       (validate_terminal_2scc): isolate the SCC, translate the G-formula
       back, ask Spot for language equivalence.
    3. Return *only* the survivors, each augmented with the extra key
       "validated_formula".

    The main reconstruction (see reconstruction.py) then treats a validated
    t2 fragment almost exactly like a successful f2 absorption:
        - the SCC states are pre-inserted into state_formula[]
        - they are removed from the bad_states "reject multi-state SCC" set
        - label() short-circuits for them
        - successor edges that point into the SCC reuse the fragment
          instead of recursing

    This is what makes the (now generalized) terminal-SCC pattern participate
    cleanly in the overall backward labeling algorithm.
    """
    candidates = find_nice_terminal_2sccs(aut)
    validated = []

    for info in candidates:
        validated_formula = validate_terminal_2scc(aut, info)
        if validated_formula is not None:
            info = dict(info)  # do not mutate caller's dicts
            info["validated_formula"] = validated_formula
            validated.append(info)

    return validated
