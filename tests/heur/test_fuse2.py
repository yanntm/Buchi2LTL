#!/usr/bin/env python3
"""Parity + soundness check for the extracted `heur.fuse2` rewrite.

The size-2 over-approximation rewrite moved from `aut2ltl.sl.heuristics.size2_overapprox`
(`try_size2_overapprox`) to `aut2ltl.heur.fuse2` (`fuse2`), with the `get_true_bdd`
hack replaced by `buddy.bddtrue` and the surgery factored into helpers. This test
runs BOTH on the same automaton over the f2 success fixture and asserts:

  * parity   — new and legacy agree (both None, or both produce an equivalent rewrite);
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
from aut2ltl.sl.heuristics.size2_overapprox import try_size2_overapprox
from tests.fixtures.f2_successes import F2_SUCCESS


def _self_loop_only(aut: "spot.twa_graph") -> bool:
    """True iff every SCC of `aut` is a single state (only cycles are self-loops)."""
    si = spot.scc_info(aut)
    return all(len(list(si.states_of(s))) == 1 for s in range(si.scc_count()))


def main() -> int:
    disagree = []
    gate_violation = []
    self_loop_hits = 0
    new_hits = legacy_hits = 0

    for f in F2_SUCCESS:
        aut = spot.formula(f).translate()           # the same input for both
        new = fuse2(aut)
        legacy = try_size2_overapprox(aut)

        new_ok = new is not None
        legacy_ok = legacy is not None
        new_hits += new_ok
        legacy_hits += legacy_ok

        # Parity: both decline, or both produce an equivalent rewrite.
        if new_ok != legacy_ok:
            disagree.append((f, new_ok, legacy_ok))
        elif new_ok and not spot.are_equivalent(new, legacy):
            disagree.append((f, "new!=legacy lang", ""))

        # The gate's promise: a returned automaton defines the input language.
        if new_ok and not spot.are_equivalent(aut, new):
            gate_violation.append(f)
        # Reported only: did the rewrite actually land in daisy's reach?
        if new_ok and _self_loop_only(new):
            self_loop_hits += 1

    n = len(F2_SUCCESS)
    print(f"formulas      : {n}")
    print(f"fuse2 hits    : {new_hits}")
    print(f"legacy hits   : {legacy_hits}")
    print(f"disagreements : {len(disagree)}")
    print(f"gate failures : {len(gate_violation)}")
    print(f"self-loop-only: {self_loop_hits}/{new_hits} (reported; daisy's reach)")
    for f, a, b in disagree[:10]:
        print(f"  DISAGREE {f!r}: new={a} legacy={b}")
    for f in gate_violation[:10]:
        print(f"  GATE-VIOLATION {f!r}")

    ok = not disagree and not gate_violation
    print("SUCCESS" if ok else "FAILURE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
