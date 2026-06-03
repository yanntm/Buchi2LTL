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

    gens, masks, valuations = extract_generators(aut, max_aps=6)
    print(f"\nExtracted {len(gens)} generators (2^{len(aut.ap())} letters).")
    print("Sample valuation for letter 0:", valuations[0] if valuations else None)

    from kr import decompose_aut, build_1level_reachability
    casc = decompose_aut(aut)
    ca = casc.build_configuration_automaton()
    print("\n--- Phase A: Configuration automaton ---")
    print("Configs:", ca["states"])
    print("Accepting configs:", casc.accepting_configs())
    if ca["states"]:
        sample_c = ca["states"][0]
        print(f"Sample trans from {sample_c}:", ca["transitions"].get(sample_c, [])[:2])

    print("\n--- Phase B starter: 1-level reachability sample ---")
    # Treat single-elem tuples as pos ints for the demo
    if casc.num_levels == 1 and ca["states"]:
        pos_map = {c: c[0] for c in ca["states"]}
        # Use trans on first config
        trans_dict = {}
        for li, nc, _v in ca["transitions"].get(ca["states"][0], []):
            trans_dict[li] = pos_map.get(nc, nc)
        reach = build_1level_reachability(1, 1, 2, "true", casc.letter_valuations, casc.aps, trans_dict)
        print("Sample reach formulas:", {k: v[:80] + "..." if len(v) > 80 else v for k, v in reach.items()})
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
