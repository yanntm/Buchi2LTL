#!/usr/bin/env python3
"""
Search for LTL formulas where the size-2 fusion heuristic (f2) successfully
activates and produces a language-equivalent automaton.

Uses the recovered working version of the heuristic (the one that actually
succeeds on interesting cases like X(p1 | F(p1 & Xp1)) ).

Has a hard 60-second timeout.

Varies number of atomic propositions and randltl tree-size (which controls
formula complexity / number of temporal operators).
"""

import sys
import time
from pathlib import Path

import spot

# Use the production size-2 absorption heuristic (the logic that was
# previously maintained as a separate "recovered working" copy has been
# reinstated into the main module).
sys.path.insert(0, str(Path(__file__).parent.parent))
from buchi2ltl.heuristics.size2_overapprox import try_size2_overapprox as try_absorb_size2_v2


TIME_LIMIT = 60.0          # seconds
TARGET = 100               # number of successful f2 cases to find

# Parameter space to explore (aps, tree_size)
# tree_size controls the size/complexity of the generated formulas
PARAM_SWEEP = [
    (2, 5), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10),
    (3, 5), (3, 6), (3, 7), (3, 8), (3, 9), (3, 10), (3, 12), (3, 14),
    (4, 5), (4, 6), (4, 7), (4, 8), (4, 9), (4, 10), (4, 12),
    (5, 5), (5, 6), (5, 7), (5, 8), (5, 9),
]

# How many formulas to generate per (aps, tree_size) before moving on
BATCH_SIZE = 80


def main():
    start_time = time.time()
    successes = []
    seen = set()
    param_index = 0

    print("=== Searching for formulas where the recovered f2 heuristic succeeds ===")
    print(f"Target: {TARGET} formulas")
    print(f"Hard timeout: {TIME_LIMIT}s")
    print(f"Parameter sweep: {len(PARAM_SWEEP)} combinations of (aps, tree_size)")
    print()

    while len(successes) < TARGET:
        elapsed = time.time() - start_time
        if elapsed > TIME_LIMIT:
            print(f"\n--- Time limit reached ({TIME_LIMIT}s) ---")
            break

        aps, tree_size = PARAM_SWEEP[param_index % len(PARAM_SWEEP)]
        param_index += 1

        remaining_time = TIME_LIMIT - elapsed
        if remaining_time < 1.0:
            break

        print(f"[{len(successes):3d}/{TARGET}]  Trying aps={aps}, tree_size={tree_size}  "
              f"(elapsed {elapsed:.1f}s)")

        try:
            gen = spot.randltl(
                aps,
                n=BATCH_SIZE,
                seed=42 + param_index,   # vary seed a bit
                tree_size=tree_size,
                simplify=2,
                output="ltl"
            )

            batch_found = 0
            for f in gen:
                if time.time() - start_time > TIME_LIMIT:
                    break

                original = str(f)
                if original in seen:
                    continue
                seen.add(original)

                try:
                    aut = f.translate("GeneralizedBuchi", "Small", "High")

                    # Try the recovered working fusion heuristic
                    massaged = try_absorb_size2_v2(aut)

                    if massaged is not None:
                        # Verify it is still language-equivalent
                        if spot.are_equivalent(aut, massaged):
                            successes.append({
                                "formula": original,
                                "aps": aps,
                                "tree_size": tree_size,
                                "states": aut.num_states(),
                            })
                            batch_found += 1
                            print(f"    ✓ FOUND #{len(successes)}: {original[:70]}")

                            if len(successes) >= TARGET:
                                break
                except Exception:
                    # Skip problematic formulas (rare)
                    continue

            if batch_found == 0:
                # Small sleep to avoid spinning too hard on hard parameter sets
                time.sleep(0.01)

        except Exception as e:
            print(f"    Error with aps={aps}, tree_size={tree_size}: {e}")
            continue

    # === Results ===
    total_time = time.time() - start_time
    print()
    print("=== Search finished ===")
    print(f"Found {len(successes)} formulas where f2 succeeded")
    print(f"Time used: {total_time:.1f}s")
    print()

    if successes:
        # Group by (aps, tree_size)
        from collections import defaultdict
        by_params = defaultdict(list)
        for s in successes:
            by_params[(s["aps"], s["tree_size"])].append(s["formula"])

        print("Breakdown by parameters:")
        for (aps, ts), formulas in sorted(by_params.items()):
            print(f"  aps={aps}, tree_size={ts}: {len(formulas)} formulas")

        print()
        print("=== All successful formulas ===")
        for i, s in enumerate(successes, 1):
            print(f"{i:3d}. {s['formula']}")

        # Save to samples/ as a stable set
        out_path = Path(__file__).parent.parent / "samples" / "f2_successes.py"
        with open(out_path, "w") as f:
            f.write('"""Formulas for which the recovered size-2 fusion heuristic (f2)\n')
            f.write('successfully produced a language-equivalent automaton.\n')
            f.write('Found using the production size2_overapprox heuristic\n')
            f.write('# (logic originally developed and verified in testing/recovered_working_fusion_heuristic.py)\n')
            f.write(f'Search time: {total_time:.1f}s\n"""\n\n')
            f.write("F2_SUCCESS = [\n")
            for s in successes:
                f.write(f'    "{s["formula"]}",\n')
            f.write("]\n\n")
            f.write("# Metadata for reproducibility\n")
            f.write("F2_SUCCESS_META = [\n")
            for s in successes:
                f.write(f'    {{"formula": "{s["formula"]}", "aps": {s["aps"]}, "tree_size": {s["tree_size"]}, "states": {s["states"]}}},\n')
            f.write("]\n")

        print(f"\nSaved {len(successes)} formulas to {out_path}")

    else:
        print("No formulas found in time. Consider relaxing parameters or increasing the time limit.")


if __name__ == "__main__":
    main()
