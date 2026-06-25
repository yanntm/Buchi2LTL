#!/usr/bin/env python3
"""Generate the mod-3 counting fixture `samples/fixtures/hoa/various/mod3_a.hoa`.

A deterministic transition-based Buchi automaton for

    L = a^{3k} . (!a)^w      (a-block length a multiple of 3, then !a forever)

This is the p >= 3 analogue of `parity_a.hoa` (the mod-2 counter): its minimal
deterministic transition monoid carries a Z/3, so it is NOT LTL-definable and the
witness extractor must report period 3. Used to pin the GAP right-action order,
which a period-2 (self-inverse) cycle cannot exercise.

Run from the repo root (rewrites the committed fixture in place):

    python3 -m tests.probes.bls.definability.witness.make_mod3_fixture
"""
from __future__ import annotations

from pathlib import Path

import buddy
import spot

OUT = Path("samples/fixtures/hoa/various/mod3_a.hoa")


def build_mod3() -> "spot.twa_graph":
    """Build the deterministic, complete, transition-Buchi automaton for L."""
    aut = spot.make_twa_graph(spot.make_bdd_dict())
    a = aut.register_ap("a")
    pos = buddy.bdd_ithvar(a)   # a
    neg = buddy.bdd_nithvar(a)  # !a
    aut.set_acceptance(1, "Inf(0)")
    aut.new_states(5)           # 0,1,2 = count mod 3 ; 3 = accept sink ; 4 = reject
    aut.set_init_state(0)
    # count a's modulo 3
    aut.new_edge(0, 1, pos, [])
    aut.new_edge(1, 2, pos, [])
    aut.new_edge(2, 0, pos, [])
    # first !a: accept iff the a-block length was a multiple of 3
    aut.new_edge(0, 3, neg, [])
    aut.new_edge(1, 4, neg, [])
    aut.new_edge(2, 4, neg, [])
    # accept sink: !a forever (the accepting loop), any a falls to reject
    aut.new_edge(3, 3, neg, [0])
    aut.new_edge(3, 4, pos, [])
    # reject sink
    aut.new_edge(4, 4, pos, [])
    aut.new_edge(4, 4, neg, [])
    aut.prop_state_acc(False)
    return aut


def main() -> int:
    aut = build_mod3()
    assert aut.is_deterministic(), "mod3 automaton must be deterministic"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(aut.to_str("hoa") + "\n", encoding="utf-8")
    print(f"wrote {OUT}  ({aut.num_states()} states, {len(aut.ap())} AP)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
