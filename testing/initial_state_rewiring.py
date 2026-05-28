#!/usr/bin/env python3
"""
Experiment: Initial state rewiring / splitting for backward LTL reconstruction.

Goal: Make the initial state a pure transient source (only outgoing edges,
no incoming edges from anywhere). This is a semantics-preserving local
automaton transformation intended to peel the initial visit out of a
cyclic SCC, making the remaining structure more amenable to our existing
reconstruction patterns.

We focus first on the case of a 2-state SCC where the initial state
is part of the cycle (as in G(p -> Xq)).

This is the first step of a broader idea involving deducing state labels
(AP valuations) inside small SCCs and applying more local rewiring patterns.

Usage:
    python3 testing/initial_state_rewiring.py "G (p -> Xq)"
"""

import sys
import subprocess
from pathlib import Path

import spot

# Make project importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from buchi2ltl.utils import simplify_ltl


def aut_to_dot(aut, title=""):
    """Return a DOT string for the automaton."""
    dot = aut.to_str("dot")
    if title:
        dot = dot.replace("digraph G {", f'digraph G {{\n  label="{title}";\n  labelloc=top;')
    return dot


def render_dot(dot_text: str, output_path: Path):
    """Write DOT and try to render PNG using graphviz 'dot'."""
    dot_path = output_path.with_suffix(".dot")
    png_path = output_path.with_suffix(".png")

    dot_path.write_text(dot_text)

    try:
        subprocess.run(
            ["dot", "-Tpng", "-o", str(png_path), str(dot_path)],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"  Rendered PNG: {png_path}")
        return png_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  Could not render PNG (graphviz 'dot' missing or failed): {e}")
        return None


def split_initial_state(aut):
    """
    Semantics-preserving rewiring:

    - Create a fresh new initial state I.
    - I gets *exactly* the outgoing transitions that the original initial state had.
    - The original initial state is left in place (now representing the state
      after the first step).
    - No edges are ever added that point to I, so I has only outgoing edges.

    This peels the very first visit to the initial state out of any cycle
    it participated in, without changing the accepted language.
    """
    if aut.num_states() == 0:
        return aut

    init = aut.get_init_state_number()

    new_aut = spot.make_twa_graph(aut.get_dict())
    new_aut.set_acceptance(aut.acc())
    new_aut.copy_ap_of(aut)

    # Fresh new initial state (will have only outgoing edges)
    new_init = new_aut.new_state()

    # Map old states -> new states (we keep all old states)
    state_map = {s: new_aut.new_state() for s in range(aut.num_states())}

    # 1. Copy every original edge (pointing at the mapped old states)
    for src in range(aut.num_states()):
        for e in aut.out(src):
            new_aut.new_edge(state_map[src], state_map[e.dst], e.cond, e.acc)

    # 2. Give the new initial state exactly the outgoing edges of the old initial
    for e in aut.out(init):
        new_aut.new_edge(new_init, state_map[e.dst], e.cond, e.acc)

    # 3. Set the new initial state
    new_aut.set_init_state(new_init)

    return new_aut


def main():
    if len(sys.argv) > 1:
        formula = sys.argv[1]
    else:
        formula = "G (p -> Xq)"

    print(f"Exploring initial-state rewiring on: {formula}")
    print("=" * 70)

    out_dir = Path("testing/debug_images")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = formula.replace(" ", "_").replace("(", "").replace(")", "").replace("->", "to")[:50]

    # === Original automaton ===
    print("\n[1] Original automaton")
    aut = spot.formula(formula).translate("GeneralizedBuchi", "Small", "High")
    print(f"    States: {aut.num_states()}, Acceptance: {aut.get_acceptance()}")
    print(f"    Init state: {aut.get_init_state_number()}")

    # SCC info
    si = spot.scc_info(aut)
    print("    SCCs:")
    for i in range(si.scc_count()):
        states = list(si.states_of(i))
        print(f"      SCC {i}: {states}, accepting={si.is_accepting_scc(i)}")

    dot_before = aut_to_dot(aut, title=f"Before: {formula}")
    png_before = render_dot(dot_before, out_dir / f"before_init_rewire_{safe_name}")

    # === Apply the rewiring ===
    print("\n[2] Applying initial state split/rewiring")
    new_aut = split_initial_state(aut)

    print(f"    New automaton has {new_aut.num_states()} states")
    print(f"    New init state: {new_aut.get_init_state_number()}")

    # Check language equivalence (our soundness guard)
    try:
        eq = spot.are_equivalent(aut, new_aut)
        print(f"    Language equivalent to original? {eq}")
    except Exception as e:
        print(f"    Equivalence check failed: {e}")

    dot_after = aut_to_dot(new_aut, title=f"After initial split: {formula}")
    png_after = render_dot(dot_after, out_dir / f"after_init_rewire_{safe_name}")

    # Show the HOA of the after version for inspection
    print("\n[3] After automaton (HOA):")
    print(new_aut.to_str("hoa"))

    print("\n=== Generated files ===")
    print(f"  Before DOT: {out_dir / f'before_init_rewire_{safe_name}.dot'}")
    if png_before:
        print(f"  Before PNG: {png_before}")
    print(f"  After DOT:  {out_dir / f'after_init_rewire_{safe_name}.dot'}")
    if png_after:
        print(f"  After PNG:  {png_after}")

    print("\nNext step: try to run reconstruction on the 'after' automaton,")
    print("or deduce state labels inside the remaining 2-state SCC.")


if __name__ == "__main__":
    main()

# ----------------------------------------------------------------------
# New pattern: Terminal 2-state SCC labeling using outgoing edges
# (as described by user, 2026-05-28)
# ----------------------------------------------------------------------

def find_terminal_two_state_sccs(aut):
    """Return list of (scc_index, sorted list of 2 states) for terminal size-2 SCCs."""
    si = spot.scc_info(aut)
    result = []
    for scc in range(si.scc_count()):
        states = list(si.states_of(scc))
        if len(states) != 2:
            continue
        is_terminal = all(si.scc_of(e.dst) == scc for st in states for e in aut.out(st))
        if is_terminal:
            result.append((scc, sorted(states)))
    return result


def compute_outgoing_or_label(aut, state):
    """Return (bdd, string) for the OR of all outgoing transition conditions from this state."""
    d = aut.get_dict()
    conds = [e.cond for e in aut.out(state)]
    if not conds:
        return spot.bddfalse, "false"
    or_bdd = conds[0]
    for c in conds[1:]:
        or_bdd = or_bdd | c
    return or_bdd, spot.bdd_format_formula(d, or_bdd)


def check_two_state_scc_labeling(aut, states):
    """
    Implements the user's proposed pattern for a 2-state SCC:
    - Compute OR of outgoing labels for each state.
    - Check if both are strictly tighter than true.
    - Optionally check overlap of the two labels.
    Returns a dict with the analysis.
    """
    d = aut.get_dict()
    labels = {}
    tight = {}
    for s in states:
        bdd, sstr = compute_outgoing_or_label(aut, s)
        labels[s] = (bdd, sstr)
        is_tight = sstr not in ("1", "true")
        tight[s] = is_tight

    s1, s2 = states
    l1_bdd, l1_str = labels[s1]
    l2_bdd, l2_str = labels[s2]

    disj = l1_bdd | l2_bdd
    disj_str = spot.bdd_format_formula(d, disj)
    covers = str(spot.formula(disj_str).simplify()) in ("1", "true")

    inter = l1_bdd & l2_bdd
    inter_str = spot.bdd_format_formula(d, inter)
    overlaps = str(spot.formula(inter_str).simplify()) not in ("0", "false")

    both_tight = tight[s1] and tight[s2]

    return {
        "states": states,
        "labels": {s: labels[s][1] for s in states},
        "both_tighter_than_true": both_tight,
        "disjunction": disj_str,
        "covers_everything": covers,
        "overlap": overlaps,
        "overlap_str": inter_str,
        "would_accept": both_tight,
    }


def analyze_all_terminal_2sccs(aut):
    """Run the labeling pattern on all terminal 2-state SCCs and print results."""
    terminal_sccs = find_terminal_two_state_sccs(aut)
    print(f"\n=== Terminal 2-state SCC labeling analysis (outgoing OR) ===")
    print(f"Found {len(terminal_sccs)} terminal 2-state SCC(s)")

    for scc_id, states in terminal_sccs:
        print(f"\nSCC {scc_id}: states {states}")
        res = check_two_state_scc_labeling(aut, states)
        for s in states:
            print(f"  State {s} label (OR outgoing): {res['labels'][s]}")
        print(f"  Both tighter than true? {res['both_tighter_than_true']}")
        print(f"  Disjunction: {res['disjunction']} (covers all? {res['covers_everything']})")
        print(f"  Overlap? {res['overlap']} ({res['overlap_str']})")
        print(f"  >>> Pattern would accept this SCC? {res['would_accept']}")
        if not res['would_accept']:
            print("      (rejected because at least one state has label 'true')")

# ----------------------------------------------------------------------
# User's refined pattern (incoming for L, outgoing for O)
# L = OR of incoming edges to the state
# O = OR of outgoing edges from the state
# Accept only if: both L tighter than true + L(A) & L(B) == false (mutually exclusive)
# Then emit: G( L(A) & X O(A)  ||  L(B) & X O(B) )
# Only applied to terminal 2-state SCCs for now.
# ----------------------------------------------------------------------

def compute_incoming_or_label(aut, state):
    """L(state) = OR of all conditions on incoming edges to this state."""
    d = aut.get_dict()
    conds = []
    for src in range(aut.num_states()):
        for e in aut.out(src):
            if e.dst == state:
                conds.append(e.cond)
    if not conds:
        return spot.bddfalse if hasattr(spot, 'bddfalse') else None, "false"
    res = conds[0]
    for c in conds[1:]:
        res = res | c
    return res, spot.bdd_format_formula(d, res)


def compute_outgoing_or_label(aut, state):
    """O(state) = OR of all conditions on outgoing edges from this state."""
    d = aut.get_dict()
    conds = [e.cond for e in aut.out(state)]
    if not conds:
        return None, "false"
    res = conds[0]
    for c in conds[1:]:
        res = res | c
    return res, spot.bdd_format_formula(d, res)


def try_extract_2state_scc_formula(aut):
    """
    Main entry point for the user's current pattern.
    Scans for terminal 2-state SCCs, applies the L/O labeling rule,
    and returns a candidate formula string if the pattern matches.
    """
    terminal_sccs = find_terminal_two_state_sccs(aut)
    candidates = []

    for scc_id, states in terminal_sccs:
        sA, sB = states

        LA_bdd, LA_str = compute_incoming_or_label(aut, sA)
        LB_bdd, LB_str = compute_incoming_or_label(aut, sB)

        # Both must be tighter than true
        tight_A = LA_str not in ("1", "true")
        tight_B = LB_str not in ("1", "true")
        if not (tight_A and tight_B):
            continue

        # Must be mutually exclusive
        inter = LA_bdd & LB_bdd
        inter_str = spot.bdd_format_formula(aut.get_dict(), inter)
        is_false = str(spot.formula(inter_str).simplify()) in ("0", "false")
        if not is_false:
            continue

        # Compute O for each
        _, OA_str = compute_outgoing_or_label(aut, sA)
        _, OB_str = compute_outgoing_or_label(aut, sB)

        # Build formula
        formula_str = f"G( ({LA_str} & X({OA_str})) | ({LB_str} & X({OB_str})) )"

        # Simplify
        try:
            simplified = str(spot.formula(formula_str).simplify())
        except:
            simplified = formula_str

        candidates.append({
            "scc": scc_id,
            "states": states,
            "L": {sA: LA_str, sB: LB_str},
            "O": {sA: OA_str, sB: OB_str},
            "formula": formula_str,
            "simplified": simplified
        })

    return candidates


def demo_user_pattern_on_automaton(aut, name="automaton"):
    """Convenience function to run the full pattern and print nicely."""
    print(f"\n=== Running user's L(incoming)/O(outgoing) pattern on {name} ===")
    cands = try_extract_2state_scc_formula(aut)
    if not cands:
        print("No terminal 2-state SCC matched the pattern.")
        return None

    for c in cands:
        print(f"\nMatched terminal SCC {c['scc']} with states {c['states']}")
        print(f"  L({c['states'][0]}) = {c['L'][c['states'][0]]}")
        print(f"  L({c['states'][1]}) = {c['L'][c['states'][1]]}")
        print(f"  O({c['states'][0]}) = {c['O'][c['states'][0]]}")
        print(f"  O({c['states'][1]}) = {c['O'][c['states'][1]]}")
        print(f"\n  Candidate formula: {c['formula']}")
        print(f"  Simplified:        {c['simplified']}")
    return cands

def extract_formula_for_terminal_2scc(aut):
    """
    User's procedure (as of 2026-05-28 message):
    1. Look for terminal size-2 *accepting* SCC.
    2. If the initial state is one of the two states, apply the initial state split first.
    3. Copy the two states into a fresh small automaton as state 0 and 1, with only their internal edges.
    4. Compute L(0) and L(1) using the (possibly split) original automaton (OR of incoming).
       Also compute O(0) and O(1) (OR of outgoing).
    5. Check the conditions: both L tighter than true + mutually exclusive.
    6. Build candidate G( L(A) & X O(A) || L(B) & X O(B) ).
    7. Validate by translating the candidate and checking language equivalence with the isolated small automaton.
       If it matches, return the validated formula + the original state indices.
    """
    terminal = find_terminal_size2_accepting_sccs(aut)  # reuse existing helper if present, else define
    if not terminal:
        return None

    init = aut.get_init_state_number()

    for scc_id, states in terminal:
        work_aut = aut
        if init in states:
            work_aut = split_initial_state(aut)

        # Isolate into small aut (states 0 and 1)
        small = spot.make_twa_graph(work_aut.get_dict())
        small.set_acceptance(work_aut.acc())
        small.copy_ap_of(work_aut)
        small.new_state()
        small.new_state()
        smap = {states[0]: 0, states[1]: 1}
        for st in states:
            for e in work_aut.out(st):
                if e.dst in states:
                    small.new_edge(smap[st], smap[e.dst], e.cond, e.acc)
        small.set_init_state(0)

        sA, sB = states
        LA_bdd, LA = compute_incoming_or_label(work_aut, sA)
        LB_bdd, LB = compute_incoming_or_label(work_aut, sB)
        _, OA = compute_outgoing_or_label(work_aut, sA)
        _, OB = compute_outgoing_or_label(work_aut, sB)

        if LA in ("1", "true") or LB in ("1", "true"):
            continue

        inter = LA_bdd & LB_bdd
        inter_str = spot.bdd_format_formula(work_aut.get_dict(), inter)
        if str(spot.formula(inter_str).simplify()) not in ("0", "false"):
            continue

        candidate = f"G( ({LA} & X({OA})) | ({LB} & X({OB})) )"

        try:
            cand_aut = spot.formula(candidate).translate("GeneralizedBuchi", "Small", "High")
            if spot.are_equivalent(small, cand_aut):
                return {
                    "states": states,
                    "L": {sA: LA, sB: LB},
                    "O": {sA: OA, sB: OB},
                    "formula": candidate,
                    "simplified": str(spot.formula(candidate).simplify())
                }
        except Exception as e:
            print("Validation error:", e)
            continue
    return None
