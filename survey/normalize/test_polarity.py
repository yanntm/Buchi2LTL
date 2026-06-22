"""Smoke test for tests/benchmark/polarity.py — the polarity dedup symmetry.

Run: python3 tests/benchmark/test_polarity.py   (prints OK / raises on failure)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from polarity import polarity_normalize_hoa, polarity_normalize_ltl  # noqa: E402


def _eq(got: str, want: str, label: str) -> None:
    assert got == want, f"{label}: got {got!r}  want {want!r}"


def test_ltl() -> None:
    # The motivating pair collapses to the first-occurrence-positive form.
    _eq(polarity_normalize_ltl("!a X F a"), "a X F !a", "ltl flip")
    _eq(polarity_normalize_ltl("a X F !a"), "a X F !a", "ltl no-flip")
    assert polarity_normalize_ltl("!a X F a") == polarity_normalize_ltl("a X F !a")

    # Per-AP, independent: a flips, b's first occurrence is positive so it stays.
    _eq(polarity_normalize_ltl("!a & b U !b"), "a & b U !b", "ltl mixed aps")

    # Constants are never flipped; surrounding text is byte-precise.
    _eq(polarity_normalize_ltl("!a | true"), "a | true", "ltl const")
    _eq(polarity_normalize_ltl("!true & a"), "!true & a", "ltl const negated")

    # !(a) is subformula negation, not a literal -> first occurrence is positive.
    _eq(polarity_normalize_ltl("!(a) & a"), "!(a) & a", "ltl paren not literal")

    # Idempotent.
    once = polarity_normalize_ltl("!a X F a")
    _eq(polarity_normalize_ltl(once), once, "ltl idempotent")


_HOA = """HOA: v1
States: 2
Start: 0
AP: 2 "a" "b"
Acceptance: 1 Inf(0)
--BODY--
State: 0
[!0 & 1] 1 {0}
State: 1
[0] 0
--END--
"""

_HOA_FLIPPED = """HOA: v1
States: 2
Start: 0
AP: 2 "a" "b"
Acceptance: 1 Inf(0)
--BODY--
State: 0
[0 & 1] 1 {0}
State: 1
[!0] 0
--END--
"""


def test_hoa() -> None:
    # AP 0 first met as !0 -> complemented everywhere; AP 1 first met as 1 -> kept.
    # State ids, {0} acceptance mark and Inf(0) are outside [...] -> untouched.
    _eq(polarity_normalize_hoa(_HOA), _HOA_FLIPPED, "hoa flip")
    once = polarity_normalize_hoa(_HOA)
    _eq(polarity_normalize_hoa(once), once, "hoa idempotent")


if __name__ == "__main__":
    test_ltl()
    test_hoa()
    print("OK")
