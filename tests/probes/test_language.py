#!/usr/bin/env python3
"""
tests/test_language.py

Unit checks for the contract-floor `Language`:
- both constructors (`of` from an automaton, `of_ltl` from an LTL formula);
- each representation builds a twa and is LANGUAGE-EQUIVALENT to the source
  (bounded spot.are_equivalent — small formulas, fast);
- det_* representations are deterministic; det_parity_sbacc is state-based;
- representations are cached (same object on the second call).

Spot only (no GAP), small inputs. Run from project root:

    python3 tests/test_language.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import spot
from aut2ltl.language import Language

# A spread of MP classes: recurrence, persistence, safety, reactivity, guarantee.
CASES = ["GFa", "FGa", "Ga", "GFa & FGb", "Fa", "a U b", "G(a -> X b)"]

REPRS = ["tgba", "det_parity_sbacc", "det_generic", "det_generic_minimal"]


def _equiv(a: "spot.twa_graph", f: "spot.formula") -> bool:
    return spot.are_equivalent(a, f.translate())


def test_ctors_and_representations() -> None:
    for s in CASES:
        f = spot.formula(s)
        for lang in (Language.of_ltl(s), Language.of(f.translate())):
            for name in REPRS:
                a = getattr(lang, name)()
                assert a.num_states() >= 1, (s, name)
                assert _equiv(a, f), f"{s}: {name} not language-equivalent"


def test_determinism_and_acceptance() -> None:
    for s in CASES:
        lang = Language.of_ltl(s)
        for name in ("det_parity_sbacc", "det_generic", "det_generic_minimal"):
            a = getattr(lang, name)()
            assert spot.is_deterministic(a), f"{s}: {name} not deterministic"
        # det_parity_sbacc must be state-based (the cascade soundness requirement).
        assert lang.det_parity_sbacc().prop_state_acc().is_true(), \
            f"{s}: det_parity_sbacc not state-based"


def test_caching() -> None:
    lang = Language.of_ltl("GFa")
    for name in REPRS:
        a1 = getattr(lang, name)()
        a2 = getattr(lang, name)()
        assert a1 is a2, f"{name} not cached"


def main() -> int:
    tests = [
        test_ctors_and_representations,
        test_determinism_and_acceptance,
        test_caching,
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
