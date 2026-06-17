#!/usr/bin/env python3
"""
tests/kr/test_decompose.py

Standalone check of the `Decompose` Composite over leaf first_success([sl, cascade]):
on a spread of split shapes (AND, OR, non-splitting, single) it produces a
language-equivalent formula. (The port-fidelity cross-check against the old
reconstruct_decomposed lived here while both existed — same techniques — and is
recorded in git history.)

GAP + Spot, small inputs (bounded). Run from project root:
    python3 tests/kr/test_decompose.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot
from aut2ltl.language import Language
from aut2ltl.first_success import first_success
from aut2ltl.portfolio.sl import sl
from aut2ltl.portfolio.decompose import Decompose
from aut2ltl.kr.aut2cas import reconstruct as cascade

CASES = ["GFa & FGb", "Ga | Fb", "FGa | FGb", "GFa", "a U b"]

dec = Decompose(first_success([sl, cascade], name="leaf"))


def test_decompose_equiv() -> None:
    for s in CASES:
        aut = spot.formula(s).translate()
        r = dec(Language.of(aut))
        assert r.ok, f"{s}: declined"
        assert spot.are_equivalent(r.formula.translate(), aut), \
            f"{s}: not language-equivalent"
        print(f"  {s:12s}  tech={r.technique_str()}")


def main() -> int:
    failed = 0
    for t in [test_decompose_equiv]:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{'ALL PASS' if not failed else f'{failed} FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
