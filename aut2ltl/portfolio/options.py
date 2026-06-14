"""
portfolio/options.py — the portfolio's OPTIONS contract.

Declares the flags this package reads — their dotted keys, defaults, and docs — as
`OptionSpec`s. Each spec is the single source of that flag's default; call sites
query `options.get(SPEC)`. The legacy `KR_GATE_*` env vars seed them (migration
bridge) until the `os.environ` call sites in this package are repointed.

What the portfolio controls via OPTIONS (so far): whether the sl gate runs at all,
the max input size it accepts, and the opt-in re-verification audit. The cleanup
of the `KR_GATE_*` env reads in `portfolio/sl.py` to `options.get(...)` is a later
(survey-gated) step; this module only declares the contract.
"""
from __future__ import annotations

from aut2ltl.options import OptionSpec

# --- the sl gate (portfolio/sl.py) ---

GATE_BUCHI2LTL = OptionSpec(
    "portfolio.gate.buchi2ltl", True,
    "run the sl gate at all (False = the pure-kr decompose path)",
    env="KR_GATE_BUCHI2LTL")

GATE_MAX_STATES = OptionSpec(
    "portfolio.gate.max_states", 60,
    "skip the sl gate on an input with more states than this",
    env="KR_GATE_MAX_STATES")

GATE_VERIFY = OptionSpec(
    "portfolio.gate.verify", False,
    "opt-in audit: re-verify each adopted sl formula against the node language",
    env="KR_GATE_VERIFY")

# The package's declared option set (the root builder aggregates these).
PORTFOLIO_OPTIONS = [GATE_BUCHI2LTL, GATE_MAX_STATES, GATE_VERIFY]

__all__ = ["GATE_BUCHI2LTL", "GATE_MAX_STATES", "GATE_VERIFY", "PORTFOLIO_OPTIONS"]
