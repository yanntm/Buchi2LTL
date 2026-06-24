#!/usr/bin/env python3
"""Extract and print the non-LTL witness for ONE HOA file (single-input probe).

    python3 -m tests.probes.witness.witness_on_hoa <file.hoa>
"""
import sys
from typing import List

import spot

from aut2ltl.language import Language
from aut2ltl.bls.definability.witness import extract_witness
from tests.probes.certificate.verify_smoke import verify_suggestive


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = argv[1]
    aut = spot.automaton(path)
    print(f"input   : {path}")
    print(f"          {aut.num_states()} states, {len(aut.ap())} AP")
    w = extract_witness(Language.of(aut), complete=True)
    if w is None:
        print("witness : NONE (transition monoid aperiodic — no group)")
        return 1
    print(f"witness : period p = {w.p}")
    print(f"  v = {w.v_str()}")
    print(f"  u = {w.u if w.u is not None else '(not completed)'}")
    if w.x_cycle is None:
        print("  x = (not completed)")
        return 0
    xp = ("; ".join(w.x_prefix) + "; ") if w.x_prefix else ""
    print(f"  x = {xp}cycle{{{'; '.join(w.x_cycle)}}}")
    # verify the completed family actually toggles on the INPUT automaton
    ok, pattern = verify_suggestive(
        aut, u=w.u or [], v=w.v, x_prefix=w.x_prefix or [], x_cycle=w.x_cycle, p=w.p
    )
    marks = "".join("1" if b else "0" for b in pattern)
    print(f"  u.v^n.x : {marks}  -> {'toggles (verified)' if ok else 'DOES NOT TOGGLE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
