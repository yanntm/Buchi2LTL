#!/usr/bin/env python3
"""
Thin compatibility / CLI entry point for the BuchiToLTL prototype.

Most of the real code now lives in the `buchi2ltl/` package.
This file keeps backward compatibility for simple usage like:

    python3 buchi2ltl.py
    from buchi2ltl import reconstruct_ltl
"""

import spot

# Re-export the public API so old imports keep working
from buchi2ltl import reconstruct_ltl, try_size2_overapprox, simplify_ltl

# Also keep the small helper that many experiments still use
def ltl_to_tgba(ltl_str):
    """Translate LTL → TGBA (same settings used by the reconstruction)."""
    f = spot.formula(ltl_str)
    aut = f.translate("GeneralizedBuchi", "Small", "High")
    return aut, f


# Simple manual test entry point (kept for convenience)
if __name__ == "__main__":
    test_cases = [
        "(p U q) & GF r",
        "FG a",
        "a U b",
        "G (p -> X p) & GF q",
        "X(p1 | F(p1 & Xp1))",   # interesting size-2 case
    ]

    for original_str in test_cases:
        print("\n" + "=" * 80)
        aut, _ = ltl_to_tgba(original_str)

        # Try the size-2 over-approximation heuristic first
        massaged = try_size2_overapprox(aut)
        technique_parts = ["sl"]
        work_aut = aut
        if massaged is not None:
            technique_parts.append("f2")
            work_aut = massaged

        recovered, per_state, _ = reconstruct_ltl(work_aut)
        technique = "+".join(technique_parts)

        print(f"Original LTL : {original_str}")
        print(f"States       : {aut.num_states()}")
        print(f"Recovered    : {recovered}")
        print(f"Technique    : {technique}")

        if recovered.startswith("UNSUPPORTED"):
            print("Status       : UNSUPPORTED")
        else:
            orig_f = spot.formula(original_str)
            rec_f = spot.formula(recovered)
            eq = spot.are_equivalent(orig_f, rec_f)
            print(f"Equivalent?  : {eq}")

            # Always show the version after Spot simplification (ltlfilt --simplify equivalent)
            simplified = simplify_ltl(recovered)
            print(f"After ltlfilt --simplify : {simplified}")
