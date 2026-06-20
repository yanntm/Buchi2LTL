"""survey.__main__ — the aut2ltl_survey CLI entry point.

Parses ``PATH ... [--logs DIR] [--use TECH ...]`` then orchestrates the run:
for each example discovered under the PATHs and each requested technique, build
via the front end and write a per-technique CSV (+ summary) into the logs dir.

Bones only — see survey/README.md for the contract.
"""
from __future__ import annotations


def main() -> int:
    # TODO: argparse (paths, --logs default ./logs, --use repeatable, `all` token)
    #       -> inputs.discover -> techniques.resolve -> build (× verify?) -> report
    raise SystemExit("survey: not yet implemented (scaffold)")


if __name__ == "__main__":
    main()
