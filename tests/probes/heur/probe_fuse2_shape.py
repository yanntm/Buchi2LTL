#!/usr/bin/env python3
"""Probe: SCC shape of one formula's automaton before/after fuse2. argv[1] = formula."""
from __future__ import annotations

import sys

import spot
from aut2ltl.heur.fuse2 import fuse2

def _sccs(aut: "spot.twa_graph") -> list:
    si = spot.scc_info(aut)
    return [
        (s, sorted(si.states_of(s)), "acc" if si.is_accepting_scc(s) else "non")
        for s in range(si.scc_count())
    ]

def main() -> int:
    f = sys.argv[1] if len(sys.argv) > 1 else "F(p2 & Xp1)"
    aut = spot.formula(f).translate()
    print(f"formula: {f}")
    print(f"BEFORE  states={aut.num_states()} sccs={_sccs(aut)}")
    out = fuse2(aut)
    if out is None:
        print("fuse2 -> None")
        return 0
    print(f"AFTER   states={out.num_states()} sccs={_sccs(out)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
