#!/usr/bin/env python3
"""
tests/bls/test_aut2cas.py

End-to-end check of the Language-native kr endpoint: `reconstruct(Language)`
builds the cascade (decompose_lang -> GAP) and returns a LTLResult whose
formula is language-equivalent to the input. Also checks the two Language ctors
(of_ltl from a formula, of from its automaton) agree through the endpoint.

GAP + Spot, small inputs (bounded). Run from project root:
    python3 tests/bls/test_aut2cas.py
"""
import sys

import spot
from aut2ltl.language import Language
from aut2ltl.bls.aut2cas import reconstruct

CASES = ["GFa", "FGa"]

def _equiv(g: "spot.formula", f: "spot.formula") -> bool:
    return spot.are_equivalent(g.translate(), f.translate())

def test_reconstruct_from_language() -> None:
    for s in CASES:
        f = spot.formula(s)
        r = reconstruct(Language.of_ltl(s))
        assert r.ok and r.formula is not None, (s, r)
        assert _equiv(r.formula, f), \
            f"{s}: reconstruct(Language) not equivalent; tech={r.technique_str()}"

def test_of_and_of_ltl_agree() -> None:
    for s in CASES:
        f = spot.formula(s)
        r1 = reconstruct(Language.of_ltl(s))
        r2 = reconstruct(Language.of(f.translate()))
        assert _equiv(r1.formula, r2.formula), s

def main() -> int:
    tests = [test_reconstruct_from_language, test_of_and_of_ltl_agree]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{'ALL PASS' if not failed else f'{failed} FAILED'} ({len(tests)} checks)")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
