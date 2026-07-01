#!/usr/bin/env python3
"""
tests/probes/gate_failsafe.py <file.hoa>

Drive the definability gate alone on one automaton: wrap an always-declining
inner translator with `definability_gate` and print the gate's outcome —
status, technique, whether `inner` ran, the diagnosis, and the witness line
when one rides the result. Shows which of the gate's three outcomes
(delegate / certified NOT_LTL / uncertified PROBABLY_NOT_LTL decline) the
input takes, with no portfolio around it.
"""
import sys
from typing import List

import spot

from aut2ltl.language import Language
from aut2ltl.result import LTLResult
from aut2ltl.bls.definability import definability_gate


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    lang = Language.of(spot.automaton(argv[1]))
    inner_ran: List[bool] = []

    def inner(l: "Language") -> LTLResult:
        inner_ran.append(True)
        return LTLResult.decline("probe inner: always declines")

    res = definability_gate(inner)(lang)
    print(f"status    : {res.status.value}")
    print(f"technique : {res.technique_str()}")
    print(f"inner ran : {bool(inner_ran)}")
    print(f"diagnosis : {res.diagnosis}")
    if res.witness is not None:
        print(f"witness   : {res.witness.serialize()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
