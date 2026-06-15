#!/usr/bin/env python3
"""
aut2ltl — the command-line front end over the portfolio.

    python3 -m aut2ltl INPUT [options]        (or the `aut2ltl` console script)

INPUT is an LTL formula string or a path to a HOA automaton file (auto-detected;
force with --ltl / --hoa). The automaton is reconstructed to an equivalent LTL
formula by the portfolio — by default the best path (sl over kr with
decompositions); with --use you cite exactly which techniques may participate.

stdout carries ONLY the formula (pipe-friendly); the verbose report (technique,
DAG/tree sizes, build time) goes to stderr and is silenced by -q. See --help.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

# Allow running as a file (python3 aut2ltl/__main__.py) as well as a module.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import spot

from aut2ltl.proc import setup_signals
from aut2ltl.options import Options, OptionSpec
from aut2ltl.language import Language, LANGUAGE_OPTIONS
from aut2ltl.portfolio import PORTFOLIO_OPTIONS, build_portfolio, TECHNIQUES
from aut2ltl.kr.options import KR_OPTIONS, FLATTEN_TREE_LIMIT
from aut2ltl.ltl.metrics import dag_metrics
from aut2ltl.ltl.printers import format_gated, to_dot

# The full declared option contract (every -O key, every --list-options row).
ALL_SPECS: List[OptionSpec] = list(PORTFOLIO_OPTIONS) + list(KR_OPTIONS) + list(LANGUAGE_OPTIONS)
_SPEC_BY_KEY = {s.key: s for s in ALL_SPECS}

_FILE_EXTS = (".hoa", ".aut", ".hoaf")


def _coerce(value: str, like: object) -> object:
    """Coerce a -O string to the native type of the spec default (bool: != '0')."""
    if isinstance(like, bool):
        return value != "0"
    if isinstance(like, int):
        return int(value)
    return value


def _epilog() -> str:
    prod = "acc, weak, buchi, cobuchi, bls, str, sl"
    wrap = "sl_driven, decompose"
    return (
        "techniques (--use), cited order = priority, no implicit fallback:\n"
        f"  producers (ladder rungs): {prod}\n"
        f"  wrappers  (wrap the ladder): {wrap}\n"
        "  --use bls            pure BLS-from-Muller\n"
        "  --use str            the integrated kr cascade (full Theorem-2 dispatch, incl. acc)\n"
        "  --use decompose,str  the kr core under AND/OR strength decomposition\n"
        "  --use buchi          Buchi leaf only; DECLINES off the Buchi class\n"
        "  --use sl,buchi,bls   first_success ladder, tried in that order\n"
        "  (omit --use)         the best default portfolio\n\n"
        "examples:\n"
        "  python3 -m aut2ltl 'GFa & GFb'\n"
        "  python3 -m aut2ltl model.hoa --use bls -O kr.fuse_letters=0\n"
        "  python3 -m aut2ltl 'F(a & X b)' -q | ltlfilt --simplify\n"
        "  python3 -m aut2ltl 'GFa & GFb' --dag | dot -Tpng -o dag.png\n"
        "  python3 -m aut2ltl --list-options\n"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aut2ltl",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Reconstruct an equivalent LTL formula from an omega-automaton "
                    "(HOA file) or an LTL formula, via the Krohn-Rhodes / heuristic portfolio.",
        epilog=_epilog(),
    )
    p.add_argument("input", nargs="?",
                   help="an LTL formula string, or a path to a HOA automaton file")

    g_in = p.add_argument_group("input")
    g_in.add_argument("--ltl", action="store_true",
                      help="force INPUT to be read as an LTL formula")
    g_in.add_argument("--hoa", action="store_true",
                      help="force INPUT to be read as a HOA file path")

    g_cfg = p.add_argument_group("configuration")
    g_cfg.add_argument("--use", metavar="T1,T2,...",
                       help="cite the techniques that may participate (comma-separated, "
                            "in priority order); omit for the best default. "
                            f"Choices: {', '.join(TECHNIQUES)}")
    g_cfg.add_argument("-O", "--option", metavar="key=value", action="append", default=[],
                       help="override a declared option (repeatable); see --list-options")
    g_cfg.add_argument("--flatten-limit", type=int, metavar="N",
                       help="max unfolded-tree nodes to print the formula as text "
                            "(over it: a placeholder); sugar for -O kr.flatten_tree_limit=N")

    g_out = p.add_argument_group("output")
    g_out.add_argument("--dag", action="store_true",
                       help="emit the formula as a graphviz dot DAG instead of LTL text "
                            "(O(distinct nodes); pure-boolean subformulas collapse to one "
                            "node) — does not explode where the flat string would")
    g_out.add_argument("-q", "--quiet", action="store_true",
                       help="print only the formula on stdout (silence the stderr report)")
    g_out.add_argument("-o", "--output", metavar="FILE",
                       help="also write the formula text to FILE")

    g_info = p.add_argument_group("info (print and exit)")
    g_info.add_argument("--list-techniques", action="store_true",
                        help="list the --use technique vocabulary and exit")
    g_info.add_argument("--list-options", action="store_true",
                        help="list every declared option (key, default, doc) and exit")
    return p


def _list_techniques() -> int:
    print("Techniques for --use (cited order = priority; no implicit fallback):")
    print("  producers (ladder rungs):")
    for t in ("acc", "weak", "buchi", "cobuchi", "bls", "str", "sl"):
        print(f"    {t}")
    print("  wrappers (wrap the ladder when cited):")
    for t in ("sl_driven", "decompose"):
        print(f"    {t}")
    return 0


def _list_options() -> int:
    print("Declared options (-O key=value); shown as  key = default : doc")
    for s in ALL_SPECS:
        print(f"  {s.key} = {s.default!r}")
        print(f"      {s.doc}")
    return 0


def _make_options(args: argparse.Namespace) -> Options:
    """Env-seeded default Options, then apply -O / --flatten-limit overrides."""
    options = Options.from_specs(ALL_SPECS)
    for item in args.option:
        if "=" not in item:
            raise ValueError(f"bad -O '{item}', expected key=value")
        key, _, raw = item.partition("=")
        spec = _SPEC_BY_KEY.get(key)
        if spec is None:
            raise ValueError(f"unknown option '{key}' (try --list-options)")
        options.set(key, _coerce(raw, spec.default))
    if args.flatten_limit is not None:
        options.set(FLATTEN_TREE_LIMIT.key, args.flatten_limit)
    return options


def _load_language(args: argparse.Namespace) -> Language:
    """Detect HOA-file vs LTL-string and build the input Language."""
    s = args.input
    is_file = args.hoa or (not args.ltl and (os.path.exists(s) or s.lower().endswith(_FILE_EXTS)))
    if is_file:
        auts = list(spot.automata(s))
        if not auts:
            raise ValueError(f"no automaton found in '{s}'")
        return Language.of(auts[0])
    return Language.of_ltl(spot.formula(s))


def _parse_techniques(use: Optional[str]) -> Optional[List[str]]:
    if use is None:
        return None
    return [t.strip() for t in use.split(",") if t.strip()]


def main(argv: Optional[List[str]] = None) -> int:
    # Forward interrupts to any external child group (GAP) before we exit, so a
    # Ctrl-C / SIGTERM doesn't orphan a multi-GB process. See aut2ltl/proc.py.
    setup_signals()
    args = build_parser().parse_args(argv)

    if args.list_techniques:
        return _list_techniques()
    if args.list_options:
        return _list_options()
    if args.input is None:
        build_parser().error("INPUT is required (an LTL formula or a HOA file path)")

    try:
        options = _make_options(args)
        techniques = _parse_techniques(args.use)
        translator = build_portfolio(options, techniques)
        lang = _load_language(args)
    except (ValueError, RuntimeError) as e:
        print(f"aut2ltl: {e}", file=sys.stderr)
        return 2

    t0 = time.monotonic()
    res = translator(lang)
    dt = time.monotonic() - t0

    if res.not_ltl:
        # Positive impossibility verdict (non-aperiodic transition monoid), not a
        # decline: the language is (probably) not LTL-definable, so no formula
        # exists. Distinct exit code (3) so callers can tell it from DECLINED (1).
        label = "NOT_LTL" if res.conclusive else "PROBABLY_NOT_LTL"
        qualifier = "not" if res.conclusive else "probably not"
        msg = f"aut2ltl: {label} — the language is {qualifier} LTL-definable"
        if res.note:
            msg += f"\n  ({res.note})"
        print(msg, file=sys.stderr)
        return 3

    if res.declined or res.formula is None:
        print("aut2ltl: DECLINED — no cited technique translated this language",
              file=sys.stderr)
        return 1

    limit = options.get(FLATTEN_TREE_LIMIT)
    text = to_dot(res.formula) if args.dag else format_gated(res.formula, limit)
    print(text)

    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")

    if not args.quiet:
        m = dag_metrics(res.formula)
        report = (
            f"technique : {res.technique_str()}\n"
            f"DAG nodes : {m.dag_nodes}\n"
            f"temporals : {m.temporal_nodes}\n"
            f"tree nodes: {m.tree_nodes}\n"
            f"sharing   : {m.sharing:.1f}x\n"
            f"build time: {dt:.3f}s"
        )
        if args.output:
            report += f"\nwritten   : {args.output}"
        print(report, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
