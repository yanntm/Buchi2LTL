"""The kanchor regression rail: byte-identical k = 1 labels, ONE HOA file.

Usage: python3 tests/probes/kanchor_rail.py <file.hoa>

Runs `Anchor` and `KAnchor(collapse=False)` (each closed over itself) on the
same input and compares outcomes. On a k = 1 input the trigger table routed
through the level-agnostic assembler must reproduce anchor's `build_final`
formula EXACTLY (hash-consed identity, not mere equivalence); declines must
agree in status. Exit code: 0 = identical outcome, 1 = divergence (printed),
2 = usage.
"""

import sys

import spot

from aut2ltl.language import Language
from aut2ltl.anchor import Anchor
from aut2ltl.kanchor import KAnchor


def main(path: str) -> int:
    lang = Language.of(spot.automaton(path))
    a = Anchor(lambda sub: a(sub))
    k = KAnchor(lambda sub: k(sub), collapse=False)
    ra, rk = a(lang), k(lang)
    print(f"anchor : status={ra.status.value} diagnosis={ra.diagnosis}")
    print(f"kanchor: status={rk.status.value} diagnosis={rk.diagnosis}")
    if ra.nok or rk.nok:
        if ra.nok and rk.nok:
            print("RAIL: ok (both decline)")
            return 0
        print("RAIL: DIVERGENCE -- one side answered, the other declined")
        return 1
    if ra.formula == rk.formula:                 # hash-consed identity
        print(f"RAIL: ok (identical formula: {ra.formula})")
        return 0
    print("RAIL: DIVERGENCE -- formulas differ")
    print(f"  anchor : {ra.formula}")
    print(f"  kanchor: {rk.formula}")
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
