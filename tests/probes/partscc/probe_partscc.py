"""Smoke-test PartScc on ONE formula's TGBA (must be a single terminal SCC).

Builds Language.of_ltl(arg), prints the TGBA shape PartScc will see (states + SCC
count), runs PartScc, and on success checks language equivalence with spot. The
leaf declines unless the whole TGBA is one SCC of size >= 2 with a tight
pairwise-disjoint L-partition. Single input, one formula per call (≤15s):

    python3 tests/partscc/probe_partscc.py 'G(p -> X q)'
"""
import sys
from typing import List

import spot  # noqa: E402

from aut2ltl.language import Language  # noqa: E402
from aut2ltl.partscc import PartScc  # noqa: E402

def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    f = spot.formula(argv[1])
    print(f"FORMULA : {f}")

    lang = Language.of_ltl(f)
    tgba = lang.tgba()                       # exactly what PartScc reads
    si = spot.scc_info(tgba)
    print(f"TGBA    : {tgba.num_states()} states, {si.scc_count()} SCC(s)")

    res = PartScc()(lang)
    if not res.ok:
        print(f"RESULT  : DECLINED ({res.diagnosis})")
        return 0
    g = res.formula
    print(f"TECHNIQUE: {sorted(res.technique)}")
    print(f"RESULT  : {g}")
    eq = spot.are_equivalent(spot.translate(f), spot.translate(g))
    print(f"EQUIV   : {eq}")
    return 0 if eq else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
