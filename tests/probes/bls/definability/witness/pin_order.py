#!/usr/bin/env python3
"""Pin the GAP right-action order of the witness lift on ONE HOA file.

Compares the witness lift's left-to-right composition (`_induced_transform`)
against GAP's right-action product (`gap.witness_eval.eval_word`), both on the real
witness `factor` and on a constructed direction-sensitive word. Defaults to the
mod-3 counter fixture (period 3, where the check is meaningful — a period-2 cycle is
its own inverse and cannot expose a flipped order).

    python3 -m tests.probes.bls.definability.witness.pin_order [file.hoa]

Exit 0 iff the order is pinned (real factor matches GAP and the direction check
confirms the convention); 1 otherwise.
"""
from __future__ import annotations

import sys
from typing import List

import spot

from aut2ltl.language import Language
from aut2ltl.bls.definability.witness.pin import check_action_order

DEFAULT = "samples/fixtures/hoa/various/mod3_a.hoa"


def main(argv: List[str]) -> int:
    path = argv[1] if len(argv) > 1 else DEFAULT
    aut = spot.automaton(path)
    print(f"input   : {path}  ({aut.num_states()} states, {len(aut.ap())} AP)")

    res = check_action_order(Language.of(aut))
    if res is None:
        print("pin     : N/A (aperiodic — no group to lift)")
        return 1

    print(f"period  : p = {res.p}")
    print(f"factor  : {res.factor}")
    print(f"  induced(factor) = {res.factor_induced}")
    print(f"  GAP    (factor) = {res.factor_gap}")
    print(f"  value match     : {'YES' if res.factor_match else 'NO'}")

    if res.direction_vacuous:
        print("direction: VACUOUS (commutative monoid — no direction-sensitive word)")
        print("RESULT  : NOT PINNED (no word exercises composition order)")
        return 1

    print(f"probe   : direction-sensitive word {res.probe_word}")
    print(f"  induced(fwd)    = {res.probe_induced_fwd}")
    print(f"  induced(rev)    = {res.probe_induced_rev}")
    print(f"  GAP    (fwd)    = {res.probe_gap}")
    fwd_ok = res.probe_induced_fwd == res.probe_gap
    rev_ok = res.probe_induced_rev != res.probe_gap
    print(f"  forward matches GAP : {'YES' if fwd_ok else 'NO'}")
    print(f"  reversal differs    : {'YES' if rev_ok else 'NO (vacuous)'}")

    print(f"RESULT  : {'PINNED (left-to-right convention confirmed)' if res.pinned else 'NOT PINNED'}")
    return 0 if res.pinned else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
