#!/usr/bin/env python3
"""tests/probes/test_result_witness.py — the witness slot on LTLResult.

The non-LTL counting family rides on a NOT_LTL result. Contract:
- it enters in exactly ONE place, the `not_definable` factory;
- `credit` propagates a NOT_LTL child's witness up (first one wins, never clobbered);
- `fail` is witness-agnostic (no second injection point);
- OK / DECLINED results never carry one.

Run from the repo root:

    python3 -m tests.probes.test_result_witness
"""
from __future__ import annotations

import sys

from aut2ltl.result import LTLResult, Status
from aut2ltl.witness import Witness


def _w(p: int) -> Witness:
    return Witness(p=p, v=["a"], factor=[1])


def test_factory_carries_witness() -> None:
    w = _w(2)
    r = LTLResult.not_definable("not LTL", "gate", witness=w)
    assert r.not_ltl and r.witness is w, "factory must carry the witness on NOT_LTL"


def test_factory_witness_optional() -> None:
    r = LTLResult.not_definable("not LTL", "gate")
    assert r.not_ltl and r.witness is None, "witness is optional"


def test_credit_propagates_witness() -> None:
    w = _w(3)
    res = LTLResult.start("portfolio")
    res.credit(LTLResult.not_definable("not LTL", "gate", witness=w))
    assert res.not_ltl, "a NOT_LTL child raises the parent to NOT_LTL"
    assert res.witness is w, "the child's witness must ride up"


def test_credit_first_witness_wins() -> None:
    first, second = _w(2), _w(3)
    res = LTLResult.start("portfolio")
    res.credit(LTLResult.not_definable("a", "g1", witness=first))
    res.credit(LTLResult.not_definable("b", "g2", witness=second))
    assert res.witness is first, "an existing witness is never clobbered"


def test_ok_and_declined_have_no_witness() -> None:
    assert LTLResult.success(None, "leaf").witness is None
    assert LTLResult.decline("nope", "leaf").witness is None


def test_fail_is_witness_agnostic() -> None:
    res = LTLResult.start("portfolio")
    res.fail(Status.NOT_LTL, "gave up")
    assert res.not_ltl and res.witness is None, "fail injects no witness"


def main() -> int:
    tests = [
        test_factory_carries_witness,
        test_factory_witness_optional,
        test_credit_propagates_witness,
        test_credit_first_witness_wins,
        test_ok_and_declined_have_no_witness,
        test_fail_is_witness_agnostic,
    ]
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
