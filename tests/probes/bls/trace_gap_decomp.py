#!/usr/bin/env python3
"""
tests/bls/trace_gap_decomp.py — dump the raw SgpDec holonomy output for one HOA.

Replays `decompose_aut`'s steps (normalize -> extract generators -> GAP script ->
run -> parse) but prints the RAW GAP stdout and the parsed cascade levels. Used to
check the LTL-definability obstruction: does the holonomy decomposition contain a
non-trivial GROUP component (=> language NOT LTL-definable), and how is it
currently labelled (`export.py` hardcodes `KIND reset`)?

Usage:
    python3 tests/bls/trace_gap_decomp.py <hoa-file>
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot  # noqa: E402

from aut2ltl.bls.extract import extract_generators  # noqa: E402
from aut2ltl.bls.gap.export import generate_gap_script  # noqa: E402
from aut2ltl.bls.gap.runner import run_gap_script  # noqa: E402
from aut2ltl.bls.gap.parse import parse_cascade_output  # noqa: E402


def main(path: str) -> int:
    aut = list(spot.automata(path))[0]
    aut = spot.postprocess(aut, "parity min even", "deterministic", "complete", "sbacc")
    print(f"=== normalized D: {aut.num_states()} states, "
          f"acc={aut.get_acceptance()} ===")

    gens, masks, valuations = extract_generators(aut, max_aps=5)
    print(f"=== {len(gens)} generators (images, 0-based) ===")
    for i, g in enumerate(gens):
        print(f"  letter {i}: {g}")

    script = generate_gap_script(gens)
    raw = run_gap_script(script, timeout=15)
    print("=== RAW GAP OUTPUT ===")
    print(raw)

    casc = parse_cascade_output(raw, generators=gens)
    print("=== PARSED CASCADE ===")
    print(f"  aperiodic: {casc.aperiodic}  "
          f"({'LTL-definable' if casc.aperiodic else 'NOT_LTL'})")
    print(f"  levels: {getattr(casc, 'num_levels', '?')}")
    for attr in ("level_sizes", "level_kinds", "levels"):
        if hasattr(casc, attr):
            print(f"  {attr}: {getattr(casc, attr)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: trace_gap_decomp.py <hoa-file>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
