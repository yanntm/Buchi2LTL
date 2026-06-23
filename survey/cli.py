"""survey.cli — argument parsing for aut2ltl_survey; delegates to survey.run.

Inputs are explicit and repeatable (no bare positionals): inline `--ltl`
formulas, `--hoa` files, and `--folder` paths (a file or dir, recursed). With
none given, print usage and exit. `--logs DIR` sends the CSV to a file (else it
prints to stdout); verification is on by default (`--no-verify` to skip).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterator, List

from survey.discovery import discover
from survey.example import Example
from survey.run import run


def _gather(ltls: List[str], hoas: List[str], folders: List[str]) -> Iterator[Example]:
    for k, formula in enumerate(ltls, start=1):
        yield Example("ltl", formula, formula, source=f"--ltl:{k}")
    for h in hoas:
        p = Path(h)
        yield Example("hoa", str(p), p.name, source=str(p))
    for d in folders:
        yield from discover([Path(d)])


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aut2ltl_survey",
        description="Run aut2ltl over examples (inline or discovered under "
                    "folders), one flat CSV per run, with optional verification.")
    p.add_argument("--ltl", action="append", default=[], metavar="FORMULA",
                   help="inline LTL formula (repeatable)")
    p.add_argument("--hoa", action="append", default=[], metavar="FILE",
                   help="HOA automaton file (repeatable)")
    p.add_argument("--folder", action="append", default=[], metavar="PATH",
                   help="file or dir, recursed for readable examples (repeatable)")
    p.add_argument("--logs", type=Path, default=None, metavar="DIR",
                   help="write the CSV here; without it, the CSV prints to stdout")
    p.add_argument("--use", action="append", default=[], metavar="TECH",
                   help="technique, passed through opaquely (repeatable); omit "
                        "for the default; 'all' = every technique (not yet supported)")
    p.add_argument("--no-verify", dest="verify", action="store_false",
                   help="skip the spot-oracle equivalence check (on by default)")
    p.add_argument("--verbose", action="store_true",
                   help="per-input live trace on stderr")
    p.add_argument("--build-timeout", type=int, default=15, metavar="S")
    p.add_argument("--equiv-timeout", type=int, default=15, metavar="S")
    return p


def main(argv: List[str] | None = None) -> int:
    p = _parser()
    args = p.parse_args(argv)
    if not (args.ltl or args.hoa or args.folder):
        p.print_help(sys.stderr)
        return 2
    examples = list(_gather(args.ltl, args.hoa, args.folder))
    if not examples:
        print("survey: no readable examples found under the given inputs",
              file=sys.stderr)
        return 2
    return run(examples, args.use, logs_dir=args.logs, verify=args.verify,
               verbose=args.verbose, build_timeout=args.build_timeout,
               equiv_timeout=args.equiv_timeout)
