"""Dump the intermediate objects of the definability oracle on ONE HOA file:
the deterministic form's size, the letters, the enriched-monoid closure, the
seed (residual classes / distinct profiles), the refined class count, the
group found (v, index, period), the chase, and the assembled family.

Usage:  python3 tests/probes/oracle_dump.py <file.hoa>

A reading aid for `oracle/algorithm.md`'s worked examples and a debugging
window on the pipeline — no verdict logic of its own.
"""
from __future__ import annotations

import sys

import spot

from aut2ltl.language import Language
from aut2ltl.bls.extract import extract_generators
from aut2ltl.bls.definability.witness.enriched import letter_elems
from aut2ltl.bls.definability.witness.support import valuation_to_letter
from aut2ltl.bls.definability.oracle.closure import close
from aut2ltl.bls.definability.oracle.family import assemble
from aut2ltl.bls.definability.oracle.profile import profile
from aut2ltl.bls.definability.oracle.quotient import find_group
from aut2ltl.bls.definability.oracle.refine import chase, refine
from aut2ltl.bls.definability.oracle.residuals import state_classes


def main(path: str) -> int:
    lang = Language.of(spot.automaton(path))
    det = lang.det_generic_minimal()
    aut = spot.postprocess(det, "deterministic", "generic", "complete")
    gens, _masks, valuations = extract_generators(aut)
    names = [valuation_to_letter(v) for v in valuations]
    print(f"D          : {aut.num_states()} states, {len(names)} letters "
          f"{names}, acc {aut.get_acceptance()}")

    letters = letter_elems(aut, valuations)
    mon = close(letters, aut.num_states(), 20000)
    if mon is None:
        print("closure    : blew the cap")
        return 2
    print(f"closure    : |EM1| = {len(mon)} elements (identity included)")

    st_cls = state_classes(aut)
    print(f"residuals  : state classes {st_cls} "
          f"({len(set(st_cls))} classes on {aut.num_states()} states)")
    lin = [tuple(st_cls[st] for (st, _m) in el) for el in mon.elems]
    acc = aut.acc()
    prof = [profile(acc, el) for el in mon.elems]
    seed = list(zip(lin, prof))
    print(f"seed       : {len(set(lin))} distinct ~lin vectors, "
          f"{len(set(prof))} distinct profiles, {len(set(seed))} seed classes")

    cls = refine(mon, seed)
    print(f"refined    : {max(cls) + 1} classes = |S(L)+ (1 adjoined)|")

    group = find_group(mon, cls)
    if group is None:
        print("verdict    : aperiodic -- LTL")
        return 0
    v_word = " ; ".join(names[li] for li in mon.rep[group.v])
    print(f"group      : v = [{v_word}] (element {group.v}), "
          f"index a = {group.a}, period c = {group.c}")
    b = chase(mon, seed, group.powers[group.a - 1], group.powers[group.a])
    if b is None:
        print("chase      : FAILED (invariant breach)")
        return 2
    print(f"chase      : b = [{' ; '.join(names[li] for li in b)}]")
    w = assemble(aut, gens, valuations, mon, lin, prof, group, b)
    if w is None:
        print("family     : FAILED to assemble")
        return 2
    shape = "omega-power" if w.omega_power else "linear"
    print(f"family     : {shape}  {w.serialize()}")
    return 3


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
