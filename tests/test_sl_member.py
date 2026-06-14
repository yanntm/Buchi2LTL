#!/usr/bin/env python3
"""
tests/test_sl_member.py

Standalone check of the `Sl` Translator: on each case it either declines or
produces a language-equivalent formula (sound-by-construction: exact on the
very-weak fragment, declines off it). (The port-fidelity cross-check against the
old try_heuristic_gate lived here while both existed — 0/10 non-identical — and is
recorded in git history.)

Spot only (no GAP), small inputs. Run from project root:
    python3 tests/test_sl_member.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import spot
from aut2ltl.language import Language
from aut2ltl.portfolio.sl import sl as sl_member

CASES = ["Ga", "Fa", "a U b", "GFa", "FGa", "Fa | Gb",
         "G(a -> X b)", "GFa & FGb", "X(a & Xa)", "G(p | F q)"]


def test_sl_equiv_or_declines() -> None:
    produced = 0
    for s in CASES:
        aut = spot.formula(s).translate()
        r = sl_member(Language.of(aut))
        if r.declined:
            continue
        produced += 1
        assert spot.are_equivalent(r.formula.translate(), aut), \
            f"{s}: Sl produced a non-equivalent formula ({r.formula})"
    print(f"  {produced}/{len(CASES)} produced (rest declined), all equivalent")


def main() -> int:
    failed = 0
    for t in [test_sl_equiv_or_declines]:
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
