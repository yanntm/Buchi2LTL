#!/usr/bin/env python3
"""
Example using a small deterministic automaton produced by Spot.

Requires: the kr package + (optionally) GAP + SgpDec for the full run.

This demonstrates the "extract then decompose" path on a real Spot aut.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import spot
from kr import decompose_aut, extract_generators, is_deterministic, check_gap_available


def main():
    # A formula whose "Deterministic" translation is small and deterministic.
    # G(p -> X q) is a classic t2 / nice terminal SCC case in the heuristic path.
    f = spot.formula("G(p -> X q)")
    aut = f.translate("Buchi", "Deterministic")
    print("Formula :", f)
    print("States  :", aut.num_states())
    print("Deterministic?", is_deterministic(aut))
    print("APs     :", [str(a) for a in aut.ap()])

    gens, masks = extract_generators(aut, max_aps=6)
    print(f"\nExtracted {len(gens)} generators (2^{len(aut.ap())} letters).")
    print("First generator image list:", gens[0])

    if check_gap_available():
        print("\nRunning holonomy decomposition via SgpDec...")
        casc = decompose_aut(aut, timeout=90)
        print("Result:", casc)
        print("state->config:", casc.state_to_config)
    else:
        print("\nGAP + SgpDec not available — skipping the actual decomposition.")
        print("Install with ./kr/install.sh and re-run.")


if __name__ == "__main__":
    main()
