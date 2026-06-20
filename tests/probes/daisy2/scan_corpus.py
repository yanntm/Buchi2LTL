"""Scan the survey corpus under best_daisy2 and report daisy2 Spot-gate failures.

A "bad validation from spot" is a daisy2 gate REJECT: daisy2 built a candidate for
a star SCC but the Spot equivalence oracle found it non-equivalent (the closed
form is incomplete there), so it declined and the cascade took over. This driver
runs each corpus formula through best_daisy2 in-process with DAISY2_TRACE on,
captures the trace per formula, and lists every formula that produced a gate
REJECT (or a gate ERROR), with the witnesses.

Usage:  python3 tests/daisy2/scan_corpus.py
"""
import os

os.environ["DAISY2_TRACE"] = "1"          # must precede the daisy2 import

import contextlib                          # noqa: E402
import io                                  # noqa: E402
import sys                                 # noqa: E402
from typing import List, Tuple            # noqa: E402

from tests.survey_formulas import SURVEY_FORMULAS   # noqa: E402
from aut2ltl.options import Options                 # noqa: E402
from aut2ltl.portfolio.build import build_portfolio  # noqa: E402
from aut2ltl.language import Language               # noqa: E402

def main() -> None:
    translator = build_portfolio(Options(), ["best_daisy2"])
    flagged: List[Tuple[str, int, int, str]] = []
    for f in SURVEY_FORMULAS:
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            res = translator(Language.of_ltl(f))
        trace = buf.getvalue()
        n_rej = trace.count("gate REJECT")
        n_err = trace.count("gate ERROR")
        if n_rej or n_err:
            flagged.append((f, n_rej, n_err, trace))
        print(f"{f:34s} {res.status.value:9s} {res.technique_str():22s} "
              f"rej={n_rej} err={n_err}")

    print(f"\n{len(flagged)}/{len(SURVEY_FORMULAS)} formulas produced a daisy2 "
          f"gate REJECT/ERROR (bad validation from spot):")
    for f, nr, ne, tr in flagged:
        print(f"\n--- {f}   (rej={nr} err={ne}) ---")
        for line in tr.splitlines():
            if "[daisy2]" in line:
                print("  " + line)

if __name__ == "__main__":
    main()
