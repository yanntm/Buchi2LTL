#!/usr/bin/env python3
"""
Search for LTL formulas where, after systematic initial-state rewiring,
we find a terminal 2-state SCC whose incoming-OR labels L(A), L(B) are:
  - Both strictly tighter than true
  - Mutually exclusive (L(A) & L(B) == false)

When found, we emit the candidate formula:
    G( L(A) & X O(A)  ||  L(B) & X O(B) )

This is the user's current pattern for terminal size-2 SCCs.

Search uses randltl with varying aps and tree_size.
Hard timeout (default 120s). Goal: 100 successes.

Usage:
    python3 testing/find_terminal_2scc_cases.py
"""

import sys
import time
from pathlib import Path
from collections import defaultdict

import spot

# Make sure we can import our local experiment code
sys.path.insert(0, str(Path(__file__).parent.parent))

from testing.initial_state_rewiring import (
    split_initial_state,
    find_terminal_two_state_sccs,
    compute_incoming_or_label,
    compute_outgoing_or_label,
)

TIME_LIMIT = 120.0      # seconds - user can change
TARGET = 100
BATCH_SIZE = 60

# Parameter sweep (aps, tree_size)
PARAM_SWEEP = [
    (2, 5), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10), (2, 12),
    (3, 5), (3, 6), (3, 7), (3, 8), (3, 9), (3, 10), (3, 12), (3, 14),
    (4, 5), (4, 6), (4, 7), (4, 8), (4, 9), (4, 10), (4, 12),
    (5, 5), (5, 6), (5, 7), (5, 8), (5, 9), (5, 10),
]


def check_user_pattern_on_scc(aut, states):
    """Return (accepted: bool, info: dict) for the user's rule on a 2-state SCC."""
    sA, sB = states

    LA_bdd, LA_str = compute_incoming_or_label(aut, sA)
    LB_bdd, LB_str = compute_incoming_or_label(aut, sB)

    tight_A = LA_str not in ("1", "true")
    tight_B = LB_str not in ("1", "true")
    both_tight = tight_A and tight_B

    inter = LA_bdd & LB_bdd
    inter_str = spot.bdd_format_formula(aut.get_dict(), inter)
    is_false = str(spot.formula(inter_str).simplify()) in ("0", "false")

    if not (both_tight and is_false):
        return False, None

    # Both checks passed → compute O and build formula
    _, OA_str = compute_outgoing_or_label(aut, sA)
    _, OB_str = compute_outgoing_or_label(aut, sB)

    formula_str = f"G( ({LA_str} & X({OA_str})) | ({LB_str} & X({OB_str})) )"

    try:
        simplified = str(spot.formula(formula_str).simplify())
    except:
        simplified = formula_str

    info = {
        "states": states,
        "L": {sA: LA_str, sB: LB_str},
        "O": {sA: OA_str, sB: OB_str},
        "formula": formula_str,
        "simplified": simplified,
    }
    return True, info


def main():
    start_time = time.time()
    successes = []
    seen = set()
    param_index = 0

    print("=== Searching for formulas with nice terminal 2-state SCCs ===")
    print(f"Target: {TARGET} formulas")
    print(f"Hard timeout: {TIME_LIMIT}s")
    print("Process: randltl → translate → ALWAYS apply initial-state split → check terminal 2-state SCCs")
    print("Pattern: L = OR(incoming), both L < true + mutually exclusive → emit G(L(A)&XO(A) || L(B)&XO(B))")
    print()

    while len(successes) < TARGET:
        elapsed = time.time() - start_time
        if elapsed > TIME_LIMIT:
            print(f"\n--- Time limit reached ({TIME_LIMIT}s) ---")
            break

        aps, tree_size = PARAM_SWEEP[param_index % len(PARAM_SWEEP)]
        param_index += 1

        if time.time() - start_time > TIME_LIMIT:
            break

        print(f"[{len(successes):3d}/{TARGET}]  Trying aps={aps}, tree_size={tree_size}  "
              f"(elapsed {elapsed:.1f}s)")

        try:
            gen = spot.randltl(
                aps,
                n=BATCH_SIZE,
                seed=42 + param_index * 7,
                tree_size=tree_size,
                simplify=2,
                output="ltl"
            )

            for f in gen:
                if time.time() - start_time > TIME_LIMIT:
                    break

                original = str(f)
                if original in seen:
                    continue
                seen.add(original)

                try:
                    aut = f.translate("GeneralizedBuchi", "Small", "High")

                    # Always apply the initial state rewiring first
                    rewired = split_initial_state(aut)

                    # Look for terminal 2-state SCCs in the rewired automaton
                    terminal = find_terminal_two_state_sccs(rewired)

                    for scc_id, states in terminal:
                        accepted, info = check_user_pattern_on_scc(rewired, states)
                        if accepted:
                            successes.append({
                                "original": original,
                                "aps": aps,
                                "tree_size": tree_size,
                                "states_in_scc": states,
                                "L": info["L"],
                                "O": info["O"],
                                "formula": info["formula"],
                                "simplified": info["simplified"],
                            })
                            print(f"    ✓ FOUND #{len(successes)}: {original[:65]}")
                            print(f"      L: {info['L']}   O: {info['O']}")
                            print(f"      → {info['simplified']}")

                            if len(successes) >= TARGET:
                                break

                    if len(successes) >= TARGET:
                        break

                except Exception:
                    continue

        except Exception as e:
            print(f"    Error: {e}")
            continue

    total_time = time.time() - start_time

    print()
    print("=== Search finished ===")
    print(f"Found {len(successes)} formulas where the pattern matched after initial-state split")
    print(f"Time used: {total_time:.1f}s")

    if not successes:
        print("No matches found within time limit.")
        return

    # Breakdown
    by_params = defaultdict(int)
    for s in successes:
        by_params[(s["aps"], s["tree_size"])] += 1

    print("\nBreakdown by (aps, tree_size):")
    for (aps, ts), count in sorted(by_params.items()):
        print(f"  aps={aps}, tree_size={ts}: {count}")

    # Save to samples/
    out_path = Path(__file__).parent.parent / "samples" / "terminal_2scc_labeled.py"
    with open(out_path, "w") as f:
        f.write('"""Formulas for which, after initial-state rewiring, we found a\n')
        f.write('terminal 2-state SCC whose incoming-OR labels L(A), L(B) are both\n')
        f.write('tighter than true and mutually exclusive.\n')
        f.write('We emit the candidate: G( L(A) & X O(A) || L(B) & X O(B) )\n')
        f.write(f'Search time: {total_time:.1f}s, target={TARGET}\n"""\n\n')
        f.write("TERMINAL_2SCC_LABELED = [\n")
        for s in successes:
            f.write(f'    "{s["original"]}",\n')
        f.write("]\n\n")
        f.write("# Detailed extraction info\n")
        f.write("TERMINAL_2SCC_DETAILS = [\n")
        for s in successes:
            f.write(f'    {{\n')
            f.write(f'        "original": "{s["original"]}",\n')
            f.write(f'        "aps": {s["aps"]}, "tree_size": {s["tree_size"]},\n')
            f.write(f'        "scc_states": {s["states_in_scc"]},\n')
            f.write(f'        "L": {s["L"]},\n')
            f.write(f'        "O": {s["O"]},\n')
            f.write(f'        "formula": "{s["formula"]}",\n')
            f.write(f'        "simplified": "{s["simplified"]}",\n')
            f.write(f'    }},\n')
        f.write("]\n")

    print(f"\nSaved {len(successes)} formulas + details to {out_path}")

    print("\n=== Sample formulas found ===")
    for i, s in enumerate(successes[:8], 1):
        print(f"{i:2d}. {s['original'][:70]}")
        print(f"     → {s['simplified']}")


if __name__ == "__main__":
    main()
