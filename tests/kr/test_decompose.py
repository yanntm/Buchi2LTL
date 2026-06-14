#!/usr/bin/env python3
"""
tests/kr/test_decompose.py

Cross-check the new `Decompose` Composite (over leaf first_success([sl, cascade]))
against the old `reconstruct_decomposed` on a spread of split shapes: AND, OR,
non-splitting (gate), single. Verdicts must be language-equivalent; technique
strings are printed (they may shift — the Composite re-minimizes per level).

GAP + Spot, small inputs (bounded). Run from project root:
    python3 tests/kr/test_decompose.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot
from aut2ltl.language import Language
from aut2ltl.combinators import first_success
from aut2ltl.portfolio.sl import sl
from aut2ltl.portfolio.decompose import Decompose
from aut2ltl.kr.aut2cas import reconstruct as cascade
from aut2ltl.portfolio.decompose_recombine import reconstruct_decomposed as old_decomposed

CASES = ["GFa & FGb", "Ga | Fb", "FGa | FGb", "GFa", "a U b"]

dec = Decompose(first_success([sl, cascade], name="leaf"))


def test_decompose_matches_old() -> None:
    for s in CASES:
        aut = spot.formula(s).translate()
        old = old_decomposed(aut)
        new = dec(Language.of(aut))
        assert old.ok and new.ok, f"{s}: old={old} new={new}"
        assert spot.are_equivalent(old.formula.translate(), new.formula.translate()), \
            f"{s}: not language-equivalent"
        print(f"  {s:12s}  old={old.technique_str():12s}  new={new.technique_str()}")


def main() -> int:
    failed = 0
    for t in [test_decompose_matches_old]:
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
