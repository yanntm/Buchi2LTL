#!/usr/bin/env python3
"""
tests/kr/test_acc_translator.py

Validate that the Acc leaf (kr/acc.reconstruct_acc) honors the CascadeTranslator
contract: casc -> ReconResult, self-gating, language-faithful when it fires.

- Bounded-fragment cases (X-ladder): result is OK, technique == {'acc'}, and the
  formula is equivalent to the original language.
- Recurrent cases (Ga, GFa, a U b, ...): result DECLINES (no false positive).

Subprocess-free, small Spot equiv per case under a budget. Run from root:

    python3 tests/kr/test_acc_translator.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.contract import ReconResult, CascadeTranslator
from aut2ltl.kr.gap import decompose_aut
from aut2ltl.kr.acc import reconstruct_acc

BOUNDED = ["a", "X a", "X X a", "a & X a", "X(a & X a)", "a | X b"]
RECURRENT = ["G a", "a U b", "F(a & b)", "G(a -> X b)", "GFa", "FGa"]


def _result(fs: str) -> ReconResult:
    return reconstruct_acc(decompose_aut(spot.formula(fs).translate()))


def test_is_cascade_translator() -> None:
    # @runtime_checkable: structural callable check.
    assert isinstance(reconstruct_acc, CascadeTranslator)


def test_bounded_fire_and_faithful() -> None:
    for fs in BOUNDED:
        r = _result(fs)
        assert r.ok, f"{fs}: expected OK, got DECLINE"
        assert r.technique == {"acc"}, f"{fs}: technique={r.technique}"
        eq = spot.are_equivalent(spot.formula(fs), r.formula)
        assert eq, f"{fs}: not equivalent to original"


def test_recurrent_declines() -> None:
    for fs in RECURRENT:
        r = _result(fs)
        assert r.declined, f"{fs}: expected DECLINE, got {r.formula}"
        assert r.formula is None


def main() -> int:
    tests = [test_is_cascade_translator, test_bounded_fire_and_faithful, test_recurrent_declines]
    failed = 0
    for t in tests:
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
