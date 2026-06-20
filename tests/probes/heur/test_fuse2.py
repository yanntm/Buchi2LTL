#!/usr/bin/env python3
"""Soundness check for the `heur.fuse2` size-2 over-approximation rewrite.

`fuse2` (in `aut2ltl.heur.fuse2`) is the extracted, self-contained rewrite (the legacy
`aut2ltl.sl.heuristics.size2_overapprox` it was lifted from is retired with the sl
engine). This test runs it over the f2 success fixture and asserts:

  * the gate — whenever `fuse2` returns an automaton, it is language-equivalent to the
    input (the soundness guarantee).

The self-loop-only rate is REPORTED, not asserted: the rewrite is best-effort and only
sometimes lands in daisy's reach (the gate promises language equality, not shape).

Bounded: each formula is a tiny automaton; the whole sweep is a few seconds.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import spot

from aut2ltl.heur.fuse2 import fuse2
from tests.fixtures.f2_successes import F2_SUCCESS


def _self_loop_only(aut: "spot.twa_graph") -> bool:
    """True iff every SCC of `aut` is a single state (only cycles are self-loops)."""
    si = spot.scc_info(aut)
    return all(len(list(si.states_of(s))) == 1 for s in range(si.scc_count()))


def main() -> int:
    gate_violation = []
    self_loop_hits = 0
    new_hits = 0

    for f in F2_SUCCESS:
        aut = spot.formula(f).translate()
        new = fuse2(aut)

        new_ok = new is not None
        new_hits += new_ok

        # The gate's promise: a returned automaton defines the input language.
        if new_ok and not spot.are_equivalent(aut, new):
            gate_violation.append(f)
        # Reported only: did the rewrite actually land in daisy's reach?
        if new_ok and _self_loop_only(new):
            self_loop_hits += 1

    n = len(F2_SUCCESS)
    print(f"formulas      : {n}")
    print(f"fuse2 hits    : {new_hits}")
    print(f"gate failures : {len(gate_violation)}")
    print(f"self-loop-only: {self_loop_hits}/{new_hits} (reported; daisy's reach)")
    for f in gate_violation[:10]:
        print(f"  GATE-VIOLATION {f!r}")

    ok = not gate_violation
    print("SUCCESS" if ok else "FAILURE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
