"""Smoke-test SlCore (pure marguerite core, delegate=decline) on ONE formula.

Builds Language.of_ltl(arg), runs sl(Λ) with Λ = first(sl(Λ), decline) (the pure
very-weak engine — decline is the floor), prints the reconstructed formula and
checks language equivalence with spot. Single input, one formula per call (≤15s):

    python3 tests/sl/probe_sl_core.py 'a U b'
"""
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import spot  # noqa: E402

from aut2ltl.language import Language  # noqa: E402
from aut2ltl.result import LTLResult, decline, first  # noqa: E402
from aut2ltl.sl.sl_core import SlCore  # noqa: E402


def _lam(lang: "Language") -> "LTLResult":
    """Λ* = fix(λ Λ. first(sl(Λ), decline)) — the pure sl engine, decline floor."""
    return first(SlCore(_lam), decline)(lang)


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    f = spot.formula(argv[1])
    print(f"FORMULA : {f}")
    res = _lam(Language.of_ltl(f))
    if not res.ok:
        print(f"RESULT  : DECLINED (status={res.status})")
        return 0
    g = res.formula
    print(f"RESULT  : {g}")
    eq = spot.are_equivalent(spot.translate(f), spot.translate(g))
    print(f"EQUIV   : {eq}")
    return 0 if eq else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
