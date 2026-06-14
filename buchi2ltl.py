#!/usr/bin/env python3
"""
Thin compatibility / CLI entry point for the BuchiToLTL prototype.

Most of the real code now lives in the `buchi2ltl/` package.
This file keeps backward compatibility for simple usage like:

    python3 buchi2ltl.py
    from buchi2ltl import reconstruct_ltl
"""

import sys
import os
import argparse
import spot

# Re-export the public API so old imports keep working
from buchi2ltl import reconstruct_ltl, try_size2_overapprox, try_terminal_2scc_with_validation, simplify_ltl

# Also keep the small helper that many experiments still use
def ltl_to_tgba(ltl_str):
    """Translate LTL → TGBA (same settings used by the reconstruction)."""
    f = spot.formula(ltl_str)
    aut = f.translate("GeneralizedBuchi", "Small", "High")
    return aut, f


def load_automaton(path_or_formula: str):
    """
    Load an automaton from either:
    - A .hoa / .aut file path
    - An LTL formula string (will be translated with the standard settings)

    Returns the automaton (and the original formula object if it came from LTL).
    """
    # Heuristic: treat as file if it exists or has a typical automaton extension
    if os.path.exists(path_or_formula) or path_or_formula.lower().endswith((".hoa", ".aut", ".hoaf")):
        try:
            auts = list(spot.automata(path_or_formula))
            if not auts:
                raise RuntimeError(f"No automaton found in {path_or_formula}")
            return auts[0], None
        except Exception as e:
            print(f"Error loading automaton from file '{path_or_formula}': {e}", file=sys.stderr)
            sys.exit(1)

    # Otherwise treat as LTL formula
    try:
        return ltl_to_tgba(path_or_formula)
    except Exception as e:
        print(f"Error parsing LTL formula '{path_or_formula}': {e}", file=sys.stderr)
        sys.exit(1)


# Simple manual test entry point + new CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BuchiToLTL: Reconstruct LTL from a TGBA (HOA file or LTL string)."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to a .hoa file or an LTL formula string. "
             "If omitted, runs the built-in test cases (legacy behavior).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show more details (states, technique, simplified formula, equivalence check when possible).",
    )
    args = parser.parse_args()

    # --- Legacy no-argument behavior (kept for backward compatibility) ---
    if args.input is None:
        test_cases = [
            "(p U q) & GF r",
            "FG a",
            "a U b",
            "G (p -> X p) & GF q",
            "X(p1 | F(p1 & Xp1))",
            "G(p -> X q)",
        ]
        for original_str in test_cases:
            print("\n" + "=" * 80)
            aut, _ = ltl_to_tgba(original_str)
            res = reconstruct_ltl(aut)
            recovered = res.formula              # spot.formula, or None if declined
            technique = res.technique_str()

            print(f"Original LTL : {original_str}")
            print(f"States       : {aut.num_states()}")
            print(f"Recovered    : {recovered}")
            print(f"Technique    : {technique}")

            if res.declined:
                print("Status       : DECLINED")
            else:
                orig_f = spot.formula(original_str)
                rec_f = recovered if isinstance(recovered, spot.formula) else spot.formula(str(recovered))
                eq = spot.are_equivalent(orig_f, rec_f)
                print(f"Equivalent?  : {eq}")
                simplified = simplify_ltl(str(recovered))
                print(f"After ltlfilt --simplify : {simplified}")
        sys.exit(0)

    # --- New single-input mode ---
    aut, orig_formula = load_automaton(args.input)

    res = reconstruct_ltl(aut)
    recovered = res.formula
    technique = res.technique_str()

    # Clean output by default (what the user asked for)
    print(recovered)

    if args.verbose:
        print(f"\nTechnique : {technique}")
        print(f"States    : {aut.num_states()}")

        if orig_formula is not None:
            # We started from an LTL string
            try:
                eq = spot.are_equivalent(orig_formula, spot.formula(recovered))
                print(f"Equivalent: {eq}")
            except Exception:
                pass

            simplified = simplify_ltl(recovered)
            if simplified != recovered:
                print(f"Simplified: {simplified}")
        else:
            # We started from a HOA file
            simplified = simplify_ltl(recovered)
            if simplified != recovered:
                print(f"Simplified: {simplified}")
