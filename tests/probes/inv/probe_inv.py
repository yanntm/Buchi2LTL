"""Smoke-test Invariant(Λ) over the pure-sl leaf on ONE formula.

Wires inv(Λ) with Λ = the pure sl engine (fix(first(sl, decline))), runs it on
Language.of_ltl(arg), prints the reconstructed formula + technique tags, and checks
language equivalence with spot. A formula whose guards don't cover 2^AP (e.g.
'a U b', Σ = a|b) exercises the strip; one that does ('F a') is vacuous and passes
through. Single input, one formula per call (≤15s):

    python3 tests/inv/probe_inv.py 'a U b'
"""
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import spot  # noqa: E402

from aut2ltl.language import Language  # noqa: E402
from aut2ltl.result import LTLResult, decline, first  # noqa: E402
from aut2ltl.daisy import Daisy  # noqa: E402
from aut2ltl.decomp.inv import Invariant  # noqa: E402


def _sl(lang: "Language") -> "LTLResult":
    """The pure sl engine: fix(λ Λ. first(sl(Λ), decline))."""
    return first(Daisy(_sl), decline)(lang)


def _lam(lang: "Language") -> "LTLResult":
    """inv over the pure sl leaf."""
    return Invariant(_sl)(lang)


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
    print(f"TECHNIQUE: {sorted(res.technique)}")
    print(f"RESULT  : {g}")
    eq = spot.are_equivalent(spot.translate(f), spot.translate(g))
    print(f"EQUIV   : {eq}")
    return 0 if eq else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
