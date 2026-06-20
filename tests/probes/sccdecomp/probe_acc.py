"""Smoke-test AccDecompose over an sl-over-kr leaf on ONE formula.

Wires AccDecompose(Λ) with Λ = first(daisy, kr-cascade): daisy peels daisies, the
kr cascade handles cores. Prints the number of top-level acceptance conjuncts of the
deterministic generic-minimal form (a genuine AND split needs >= 2), the
reconstructed formula + technique tags, and a spot equivalence check. Single input,
one formula per call (≤15s; kr calls GAP):

    python3 tests/sccdecomp/probe_acc.py 'GFa & GFb'
"""
import sys
from typing import List

import spot  # noqa: E402

from aut2ltl.language import Language  # noqa: E402
from aut2ltl.daisy import Daisy  # noqa: E402
from aut2ltl.decomp.acceptance import AccDecompose  # noqa: E402
from aut2ltl.decomp.acceptance.acceptance import conjunct_pieces  # noqa: E402
from aut2ltl.bls.aut2cas import as_translator  # noqa: E402
from aut2ltl.bls.hierarchy_class import make_hierarchy_class  # noqa: E402

_STR = as_translator(make_hierarchy_class())

def _leaf(lang: "Language") -> "LTLResult":
    """Λ = first(daisy(Λ), kr-cascade)."""
    r = Daisy(_leaf)(lang)
    return r if not r.declined else _STR(lang)

def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    f = spot.formula(argv[1])
    print(f"FORMULA  : {f}")

    lang = Language.of_ltl(f)
    print(f"CONJUNCTS: {len(conjunct_pieces(lang.det_generic_minimal()))}")

    res = AccDecompose(_leaf)(lang)
    if not res.ok:
        print(f"RESULT   : NON-ANSWER (status={res.status})")
        return 0
    g = res.formula
    print(f"TECHNIQUE: {sorted(res.technique)}")
    print(f"RESULT   : {g}")
    eq = spot.are_equivalent(spot.translate(f), spot.translate(g))
    print(f"EQUIV    : {eq}")
    return 0 if eq else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
