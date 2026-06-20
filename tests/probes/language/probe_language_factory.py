"""Probe the Language factory: interning (cache) and input cleanup.

Checks that Language.of_ltl / Language.of intern on the literal arg (same input ->
the same Language object, even across a commutative re-spelling that canonicalizes
to the same string), and that the base representation is cleaned (unused APs
dropped, redundant acceptance simplified) while the language is preserved.
Self-contained (≤15s):

    python3 tests/language/probe_language_factory.py
"""
from typing import List

import spot  # noqa: E402

from aut2ltl.language import Language  # noqa: E402

# One state, three APs declared but only a,b used, always-accepting self-loop.
_HOA = """HOA: v1
States: 1
Start: 0
AP: 3 "a" "b" "c"
Acceptance: 1 Inf(0)
--BODY--
State: 0
[0 | 1] 0 {0}
--END--
"""

def _aps(aut: "spot.twa_graph") -> List[str]:
    return sorted(str(x) for x in aut.ap())

def main() -> int:
    print("--- interning ---")
    print(f"  of_ltl('G a') twice -> same object:        {Language.of_ltl('G a') is Language.of_ltl('G a')}")
    print(f"  of_ltl('a & b') vs 'b & a' -> same object: {Language.of_ltl('a & b') is Language.of_ltl('b & a')}")
    raw = spot.automaton(_HOA)
    print(f"  of(aut) twice -> same object:              {Language.of(raw) is Language.of(raw)}")

    print("\n--- cleanup on the base ---")
    base = Language.of(spot.automaton(_HOA)).tgba()
    print(f"  raw  aps={_aps(spot.automaton(_HOA))}  acc={spot.automaton(_HOA).acc()}")
    print(f"  base aps={_aps(base)}  acc={base.acc()}")
    print(f"  unused 'c' dropped:        {'c' not in _aps(base)}")
    print(f"  language preserved (EQUIV): {spot.are_equivalent(spot.automaton(_HOA), base)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
