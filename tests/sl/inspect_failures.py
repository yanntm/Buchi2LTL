#!/usr/bin/env python3
"""
Small helper to inspect failing formulas from an evaluate.py CSV.
Shows the original formula, per-state reconstruction, and equivalence.
"""

import csv
import sys
import spot
from aut2ltl.sl.reconstruction import reconstruct_ltl

def inspect(csv_path):
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        fails = [row for row in reader if row["equivalent"] != "yes" or row["error"]]

    if not fails:
        print("No failures found in", csv_path)
        return

    print(f"=== Inspecting {len(fails)} failures from {csv_path} ===\n")

    for i, row in enumerate(fails, 1):
        print(f"--- Failure #{i} ---")
        print(f"Original : {row['original']}")
        print(f"States   : {row['states']}")
        print(f"Acceptance: {row['acceptance']}")
        if row["error"]:
            print(f"Error    : {row['error']}")
        
        try:
            f = spot.formula(row["original"])
            aut = f.translate("GeneralizedBuchi", "Small", "High")
            rec, per_state = reconstruct_ltl(aut)
            print(f"Recovered: {rec}")
            print("Per-state reconstruction:")
            for q, phi in sorted(per_state.items()):
                print(f"  state {q}: {phi}")
            orig_f = spot.formula(row["original"])
            if rec.startswith("UNSUPPORTED"):
                print("Equivalent? : N/A (UNSUPPORTED)")
            else:
                rec_f = spot.formula(rec)
                eq = spot.are_equivalent(orig_f, rec_f)
                print(f"Equivalent? : {eq}")
        except Exception as e:
            print(f"(Re-analysis failed: {e})")
        print()

if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "testing/small_failures2.csv"
    inspect(csv_file)
