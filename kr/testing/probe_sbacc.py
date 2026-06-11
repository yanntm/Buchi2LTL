#!/usr/bin/env python3
"""
kr/testing/probe_sbacc.py

Probe: is the transition-based acceptance from `postprocess("parity min even",
"deterministic", "complete")` the root cause of the GFa -> "true" failure?

Compares the current normalization vs adding "sbacc" (state-based acceptance)
for a few key formulas, printing states, acceptance, and whether the
acceptance marks sit on states (every out-edge of a state same-marked) or
genuinely on edges.

Run: python3 kr/testing/probe_sbacc.py [formulas...]
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

DEFAULT = ["GFa", "FGa", "G(a -> F b)", "a U b", "Fa", "Ga", "G(a -> X b)", "Fa | Gb"]


def edge_acc_is_state_consistent(aut) -> bool:
    """True if all out-edges of each state carry identical acc marks
    (i.e., transition-based marks are really state-based in disguise)."""
    for s in range(aut.num_states()):
        marks = {tuple(e.acc.sets()) for e in aut.out(s)}
        if len(marks) > 1:
            return False
    return True


def show(formula_str: str):
    f = spot.formula(formula_str)
    base = f.translate()

    cur = spot.postprocess(base, "parity min even", "deterministic", "complete")
    sb = spot.postprocess(base, "parity min even", "deterministic", "complete", "sbacc")

    print(f"--- {formula_str} ---")
    print(f"  current : states={cur.num_states()} acc={cur.get_acceptance()} "
          f"state-consistent-marks={edge_acc_is_state_consistent(cur)}")
    print(f"  +sbacc  : states={sb.num_states()} acc={sb.get_acceptance()} "
          f"state-consistent-marks={edge_acc_is_state_consistent(sb)} "
          f"sb-prop={bool(sb.prop_state_acc())}")
    eq = spot.are_equivalent(cur, sb)
    print(f"  equivalent to each other: {eq}")


def main():
    cases = sys.argv[1:] or DEFAULT
    for fs in cases:
        show(fs)


if __name__ == "__main__":
    main()
