#!/usr/bin/env python3
"""
tests/test_contract_combinators.py

Unit checks for the contract floor and the first composite combinator:
- LTLFormulaResult OK / DECLINED basics.
- CascadeTranslator Protocol is importable and runtime-checkable.
- first_success: short-circuits on the first OK stage, passes the winner's
  LTLFormulaResult (incl. technique) through unchanged, and declines when every
  stage declines.

No Spot, no GAP — pure contract algebra, fast. Run from project root:

    python3 tests/test_contract_combinators.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from aut2ltl.contract import LTLFormulaResult, Translator, CascadeTranslator, OK, DECLINED
from aut2ltl.combinators import first_success


def test_ltlformularesult_basics() -> None:
    ok = LTLFormulaResult(formula="F", technique={"buchi"})
    assert ok.ok and not ok.declined and ok.status == OK
    dec = LTLFormulaResult.decline({"acc"})
    assert dec.declined and not dec.ok and dec.formula is None and dec.status == DECLINED


def test_protocol_runtime_checkable() -> None:
    # A CascadeTranslator member is a named callable (fixed `name` + __call__).
    class Member:
        name = "x"
        def __call__(self, casc) -> LTLFormulaResult:
            return LTLFormulaResult.decline()
    assert isinstance(Member(), CascadeTranslator)

    # A bare function lacks the fixed `name`, so it is NOT a CascadeTranslator
    # member — but it still satisfies Translator (no name in that contract).
    def bare(twa) -> LTLFormulaResult:
        return LTLFormulaResult.decline()
    assert not isinstance(bare, CascadeTranslator)
    assert isinstance(bare, Translator)


def test_first_success_short_circuits() -> None:
    calls = []

    def s_decline(x): calls.append("a"); return LTLFormulaResult.decline()
    def s_ok(x): calls.append("b"); return LTLFormulaResult(formula="F", technique={"buchi"})
    def s_never(x): calls.append("c"); return LTLFormulaResult(formula="Z")

    chain = first_success([s_decline, s_ok, s_never], name="chain")
    r = chain("input")
    assert r.ok and r.formula == "F" and r.technique == {"buchi"}, r
    assert calls == ["a", "b"], calls          # s_never must not run


def test_first_success_all_decline() -> None:
    chain = first_success([lambda x: LTLFormulaResult.decline(),
                           lambda x: LTLFormulaResult.decline()], name="chain")
    assert chain("x").declined


def main() -> int:
    tests = [
        test_ltlformularesult_basics,
        test_protocol_runtime_checkable,
        test_first_success_short_circuits,
        test_first_success_all_decline,
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
