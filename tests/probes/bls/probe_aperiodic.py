#!/usr/bin/env python3
"""
tests/bls/probe_aperiodic.py — does the transition monoid carry a group?

LTL-definability of an omega-regular language == its deterministic automaton is
counter-free == its transition monoid is APERIODIC (group-free). SgpDec's
holonomy decomposition still succeeds on a non-aperiodic monoid (it produces
group components), so the cascade build is NOT a usable oracle by itself. This
probe asks the question directly: build T = Semigroup(gens) over the normalized
deterministic D and print `IsAperiodicSemigroup(T)` (the `Semigroups` package,
already loaded by SgpDec). False => language is NOT LTL-definable.

Usage:
    python3 tests/bls/probe_aperiodic.py <hoa-file> ...
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

import spot  # noqa: E402

from aut2ltl.bls.extract import extract_generators  # noqa: E402
from aut2ltl.bls.gap.export import _format_transformation  # noqa: E402
from aut2ltl.bls.gap.runner import run_gap_script  # noqa: E402

def _aperiodicity_script(gens: List[List[int]]) -> str:
    body = ",\n    ".join(_format_transformation(g) for g in gens)
    return (
        'LoadPackage("Semigroups");\n'
        f'gens := [\n    {body}\n];\n'
        'T := Semigroup(gens);\n'
        'Print("SIZE: ", Size(T), "\\n");\n'
        'Print("APERIODIC: ", IsAperiodicSemigroup(T), "\\n");\n'
        'QUIT;\n'
    )

def probe(path: str) -> None:
    aut = list(spot.automata(path))[0]
    aut = spot.postprocess(aut, "parity min even", "deterministic", "complete", "sbacc")
    gens, _, _ = extract_generators(aut, max_aps=5)
    raw = run_gap_script(_aperiodicity_script(gens), timeout=15)
    size = aper = "?"
    for line in raw.splitlines():
        if line.startswith("SIZE:"):
            size = line.partition(":")[2].strip()
        elif line.startswith("APERIODIC:"):
            aper = line.partition(":")[2].strip()
    ltl = {"true": "LTL-definable", "false": "NOT_LTL"}.get(aper, "?")
    print(f"  {Path(path).name:34.34s} states={aut.num_states():>2} "
          f"|T|={size:>4} aperiodic={aper:<5} -> {ltl}")

def main(paths: List[str]) -> int:
    for p in paths:
        probe(p)
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: probe_aperiodic.py <hoa-file> ...", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
