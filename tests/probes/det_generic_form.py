#!/usr/bin/env python3
"""
tests/probes/det_generic_form.py <file.hoa>

Print the form the LTL-definability tester actually reads for an input
automaton — `Language.det_generic_minimal()`, then its completion (the tester
completes before extracting generators) — followed by the tester's cached
verdict `(definable, conclusive)`. Makes visible any normalization the
Language pipeline applies on the way (e.g. rewriting a modular-counter state
structure into an aperiodic one), which decides whether the transition-monoid
group of the raw input ever reaches GAP.
"""
import sys
from typing import List

import spot

from aut2ltl.language import Language
from aut2ltl.bls.definability import label_ltl_definable


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    lang = Language.of(spot.automaton(argv[1]))
    det = lang.det_generic_minimal()
    complete = spot.postprocess(det, "deterministic", "generic", "complete")
    print("--- det_generic_minimal, completed (the tester's input) ---")
    print(complete.to_str("hoa"))
    definable, conclusive = label_ltl_definable(lang)
    print(f"--- verdict: definable={definable} conclusive={conclusive} ---")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
