"""Probe Daisy with the kr default strength cascade ('str') as second delegate.

Wires the fixpoint  Λ* = fix(λ Λ. first(sl(Λ), str))  where
str = as_translator(make_hierarchy_class()) — sl peels daisy envelopes, the
kr cascade handles the multi-state-SCC cores it delegates. Runs ONE formula per
invocation (≤15s; the cascade calls GAP), prints the result, its technique tags,
and a spot equivalence check:

    python3 tests/sl/probe_sl_over_str.py 'G(a -> F b)'
"""
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import spot  # noqa: E402

from aut2ltl.language import Language  # noqa: E402
from aut2ltl.result import LTLResult, first  # noqa: E402
from aut2ltl.daisy import Daisy  # noqa: E402
from aut2ltl.bls.aut2cas import as_translator  # noqa: E402
from aut2ltl.bls.hierarchy_class import make_hierarchy_class  # noqa: E402

_STR = as_translator(make_hierarchy_class())


def _lam(lang: "Language") -> "LTLResult":
    """Λ* = fix(λ Λ. first(sl(Λ), str)): the daisy peel, else the kr cascade."""
    return first(Daisy(_lam), _STR)(lang)


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    f = spot.formula(argv[1])
    print(f"FORMULA : {f}")
    res = _lam(Language.of_ltl(f))
    if not res.ok:
        print(f"RESULT  : NON-ANSWER (status={res.status})")
        return 0
    g = res.formula
    print(f"TECHNIQUE: {sorted(res.technique)}")
    print(f"RESULT  : {g}")
    eq = spot.are_equivalent(spot.translate(f), spot.translate(g))
    print(f"EQUIV   : {eq}")
    return 0 if eq else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
