"""Run the `kanchor` translator on ONE HOA file and check its read-off.

Usage: python3 tests/probes/kanchor_probe.py <file.hoa>

Loads the automaton and runs `KAnchor` closed over itself (`Λ = KAnchor(Λ)` —
exits strictly descend the SCC DAG, so the recursion bottoms out at terminal
components; a sub-language whose component is not anchored at any level
poisons the peel). Prints the resulting label and — on OK — checks language
equivalence of the formula against the input with spot. Exit code: 0 = OK and
equivalent, 1 = OK but NOT equivalent (a real bug), 2 = declined / NOT_LTL
(reason printed).
"""

import sys

import spot

from aut2ltl.language import Language
from aut2ltl.kanchor import KAnchor


def main(path: str) -> int:
    aut = spot.automaton(path)
    lang = Language.of(aut)
    rec = KAnchor(lambda sub: rec(sub))      # the self-fixpoint Λ = KAnchor(Λ)
    res = rec(lang)
    print(f"status={res.status.value} technique={res.technique_str()} "
          f"diagnosis={res.diagnosis}")
    if res.nok:
        return 2
    print(f"LTL: {res.formula}")
    cand = res.formula.translate("GeneralizedBuchi", "Small", "High")
    if spot.are_equivalent(aut, cand):
        print("VERIFY: ok (language-equivalent)")
        return 0
    print("VERIFY: FAIL -- formula is NOT language-equivalent to the input")
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
