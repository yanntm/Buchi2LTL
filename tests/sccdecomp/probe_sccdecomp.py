"""Smoke-test SccDecompose over an sl-over-kr leaf on ONE formula.

Wires sccdecomp(Λ) with Λ = first(sl, kr-cascade): sl peels daisies, the kr
cascade handles cores. Prints the number of accepting SCCs of the input automaton
(so a genuine split needs >= 2), the reconstructed formula + technique tags, and a
spot equivalence check. Single input, one formula per call (≤15s; kr calls GAP):

    python3 tests/sccdecomp/probe_sccdecomp.py 'Ga | Gb'
"""
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import spot  # noqa: E402

from aut2ltl.language import Language  # noqa: E402
from aut2ltl.daisy import Daisy  # noqa: E402
from aut2ltl.sccdecomp import SccDecompose  # noqa: E402
from aut2ltl.sccdecomp.restrict import accepting_sccs, ensure_marked  # noqa: E402
from aut2ltl.kr.aut2cas import as_translator  # noqa: E402
from aut2ltl.kr.hierarchy_class import make_hierarchy_class  # noqa: E402

_STR = as_translator(make_hierarchy_class())


def _leaf(lang: "Language") -> "LTLResult":
    """Λ = first(sl(Λ), kr-cascade)."""
    r = Daisy(_leaf)(lang)
    return r if not r.declined else _STR(lang)


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    f = spot.formula(argv[1])
    print(f"FORMULA : {f}")

    lang = Language.of_ltl(f)
    print(f"ACC SCCs: {len(accepting_sccs(ensure_marked(lang.tgba())))}")

    res = SccDecompose(_leaf)(lang)
    if not res.ok:
        print(f"RESULT  : NON-ANSWER (status={res.status})")
        return 0
    g = res.formula
    print(f"TECHNIQUE: {sorted(res.technique)}")
    print(f"RESULT  : {g}")
    eq = spot.are_equivalent(spot.translate(f), spot.translate(g))
    print(f"EQUIV   : {eq}")
    return 0 if eq else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
