#!/usr/bin/env python3
"""
tests/probes/witness/test_witness.py — unit checks for the non-LTL witness extractor.

Real-use path: a `Language` (built as the CLI builds it) handed to `extract_witness`
exactly as the cascade gate hands it the same form. Two contrasting inputs:

- the counter example `parity_a.hoa` (L = a^{2k}(!a)^w) — not LTL-definable, mod-2
  counting: a witness with period 2 is expected;
- an LTL formula control (`GFa`) — LTL-definable, aperiodic, no group: no witness
  is expected (the GAP script reports NOWITNESS, `extract_witness` returns None).

GAP-bearing, small inputs (fast). Run from the repo root:

    python3 -m tests.probes.witness.test_witness
"""

from __future__ import annotations

import sys
from typing import List

import spot

from aut2ltl.language import Language
from aut2ltl.bls.extract import extract_generators
from aut2ltl.bls.definability.witness import extract_witness
from tests.probes.certificate.verify_smoke import verify_suggestive

PARITY = "samples/fixtures/hoa/various/parity_a.hoa"
CONTROL = "GFa"


def _counter_lang() -> "Language":
    return Language.of(spot.automaton(PARITY))


def _compose(gens: List[List[int]], factor: List[int]) -> List[int]:
    """The transformation induced by reading the factor word (1-based indices)."""
    n = len(gens[0])
    t = list(range(n))
    for i in factor:
        g = gens[i - 1]
        t = [g[t[s]] for s in range(n)]
    return t


def _max_orbit(t: List[int]) -> int:
    """Length of the longest cycle of the functional graph of `t`."""
    best = 1
    for s in range(len(t)):
        seen: List[int] = []
        x = s
        while x not in seen:
            seen.append(x)
            x = t[x]
        best = max(best, len(seen) - seen.index(x))
    return best


def test_counter_example_has_witness() -> None:
    w = extract_witness(_counter_lang())
    assert w is not None, "expected a witness on the non-LTL counter example"
    assert w.p == 2, f"mod-2 counter: expected period 2, got {w.p}"
    assert w.v, "witness word v is empty"


def test_lift_is_faithful() -> None:
    lang = _counter_lang()
    w = extract_witness(lang)
    assert w is not None
    aut = spot.postprocess(lang.det_generic_minimal(),
                           "deterministic", "generic", "complete")
    gens, _m, _v = extract_generators(aut)
    orbit = _max_orbit(_compose(gens, w.factor))
    assert orbit == w.p, f"reading v induces orbit {orbit}, expected period {w.p}"


def test_ltl_control_has_no_witness() -> None:
    w = extract_witness(Language.of_ltl(CONTROL))
    assert w is None, f"LTL control {CONTROL!r} should yield no witness, got {w}"


def test_completed_family_toggles() -> None:
    """Stage 2: u, x synthesised from the automaton; the fully self-generated
    u.v^n.x toggles membership on the INPUT automaton."""
    w = extract_witness(_counter_lang(), complete=True)
    assert w is not None and w.complete, f"expected a completed family, got {w}"
    aut = spot.automaton(PARITY)
    ok, pattern = verify_suggestive(
        aut, u=w.u, v=w.v, x_prefix=w.x_prefix, x_cycle=w.x_cycle, p=w.p
    )
    marks = "".join("1" if b else "0" for b in pattern)
    assert ok, f"completed family did not toggle (pattern {marks})"


def main() -> int:
    tests = [
        test_counter_example_has_witness,
        test_lift_is_faithful,
        test_ltl_control_has_no_witness,
        test_completed_family_toggles,
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
