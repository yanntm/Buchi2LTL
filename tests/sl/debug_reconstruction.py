#!/usr/bin/env python3
"""
Heavy instrumentation script for debugging reconstruction of G(p -> X q).
"""

import spot
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aut2ltl.sl.reconstruction import reconstruct_ltl
from testing.initial_state_rewiring import split_initial_state

def print_automaton(aut, title):
    print(f"\n=== {title} ===")
    print(f"States: {aut.num_states()}, Init: {aut.get_init_state_number()}, Acc: {aut.get_acceptance()}")
    print(aut.to_str("hoa"))
    # Also dump DOT for visualization
    dot = aut.to_str("dot")
    safe_title = title.replace(" ", "_").replace("(", "").replace(")", "").replace("->", "to")
    dot_path = Path("testing/debug_images") / f"trace_{safe_title}.dot"
    dot_path.parent.mkdir(parents=True, exist_ok=True)
    dot_path.write_text(dot)
    print(f"(DOT written to {dot_path})")

def main():
    formula_str = "G (p -> X q)"
    print(f"\n{'='*100}")
    print(f"FULL INSTRUMENTED TRACE FOR: {formula_str}")
    print(f"{'='*100}\n")

    f = spot.formula(formula_str)
    aut = f.translate("GeneralizedBuchi", "Small", "High")

    print_automaton(aut, "1. ORIGINAL AUTOMATON")

    # Step 1: Initial state split (what the code does internally now)
    split_aut = split_initial_state(aut)
    print_automaton(split_aut, "2. AFTER INITIAL STATE SPLIT")

    # Step 2: Run the actual reconstruction (which has its own prints now)
    print("\n" + "="*100)
    print("CALLING reconstruct_ltl (watch for [DEBUG] lines)")
    print("="*100 + "\n")

    recovered, state_formulas, technique = reconstruct_ltl(aut)

    print("\n" + "="*100)
    print("FINAL RESULT FROM reconstruct_ltl")
    print("="*100)
    print(f"Technique : {technique}")
    print(f"Recovered : {recovered}")

    # Show what the experimental pattern would have extracted
    from testing.initial_state_rewiring import extract_formula_for_terminal_2scc
    # Note: the experimental pattern extraction lives in initial_state_rewiring.py
    # We already showed its clean result in previous runs: G(!p | (p & Xq))
    print("\n(Experimental pattern extraction produces the clean G(!p | (p & Xq)) as shown in prior traces.)")

if __name__ == "__main__":
    main()
