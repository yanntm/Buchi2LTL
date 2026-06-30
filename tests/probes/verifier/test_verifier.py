#!/usr/bin/env python3
"""Spec/smoke for `aut2ltl.verifier` and the `Witness` round-trip.

Asserts, on the real mod3 counter:
  * `Witness.serialize` / `Witness.parse` is identity (complete + incomplete);
  * `verify` toggles with period 3 on a genuine witness (pattern 1001001);
  * a tampered tail does not toggle (REJECT);
  * an incomplete family is unverifiable — `verify` returns `(None, [])`, which the
    survey reads as FAIL (a NOT_LTL claim with no replayable certificate).

    python3 -m tests.probes.verifier.test_verifier
"""
from __future__ import annotations

import sys

import spot

from aut2ltl.witness import Witness
from aut2ltl.verifier import verify

MOD3 = "samples/validation/hoa/mod3_a.hoa"


def _roundtrip_ok() -> bool:
    cases = [
        Witness(p=3, v=["a", "a"], factor=[1], u=[], x_prefix=[], x_cycle=["!a"]),
        Witness(p=2, v=["a"], factor=[1], u=["b"], x_prefix=["c"], x_cycle=["!a", "b"]),
        Witness(p=3, v=["a", "a"], factor=[1]),  # incomplete
    ]
    ok = True
    for w in cases:
        s = w.serialize()
        w2 = Witness.parse(s)
        same = (w2.serialize() == s and w.p == w2.p and w.v == w2.v
                and w.u == w2.u and w.x_prefix == w2.x_prefix
                and w.x_cycle == w2.x_cycle and w.complete == w2.complete)
        print(f"  round-trip {'OK ' if same else '*** FAIL'}: {s}")
        ok &= same
    return ok


def _verify_ok() -> bool:
    aut = spot.automaton(MOD3)
    ok = True

    w = Witness(p=3, v=["a", "a"], factor=[1], u=[], x_prefix=[], x_cycle=["!a"])
    res, pat = verify(aut, w)
    marks = "".join("1" if b else "0" for b in pat)
    good = (res is True and marks == "1001001")
    print(f"  genuine          {'OK ' if good else '*** FAIL'}: {marks} -> {res}")
    ok &= good

    w_bad = Witness(p=3, v=["a", "a"], factor=[1], u=[], x_prefix=[], x_cycle=["a"])
    res, pat = verify(aut, w_bad)
    good = (res is False)
    print(f"  tampered tail    {'OK ' if good else '*** FAIL'}: "
          f"{''.join('1' if b else '0' for b in pat)} -> {res}")
    ok &= good

    w_inc = Witness(p=3, v=["a", "a"], factor=[1])
    res, pat = verify(aut, w_inc)
    good = (res is None and pat == [])
    print(f"  incomplete       {'OK ' if good else '*** FAIL'}: -> {res} (unverifiable)")
    ok &= good

    return ok


def main() -> int:
    all_ok = _roundtrip_ok()
    all_ok &= _verify_ok()
    print("SUCCESS" if all_ok else "FAILURE")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
