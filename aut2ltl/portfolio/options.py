"""
portfolio/options.py — the portfolio's OPTIONS contract.

Declares the flags this package reads — their dotted keys, defaults, and docs — as
`OptionSpec`s. Each spec is the single source of that flag's default; call sites
query `options.get(SPEC)`. Keys are hierarchical and name the CURRENT code (the
`Sl` Translator in `portfolio/sl.py`), not the obsolete "gate"/"buchi2ltl" roles.
`env=` keeps the legacy var as a seeding bridge until the `os.environ` call sites
are repointed (a later, survey-gated step); this module only declares the contract.

What the portfolio controls via OPTIONS (so far): whether the `Sl` gate runs at
all, the max input size it accepts, and the opt-in re-verification audit.
"""
from __future__ import annotations

from aut2ltl.options import OptionSpec

# --- the Sl gate (portfolio/sl.py) ---

SL_ENABLED = OptionSpec(
    "portfolio.sl.enabled", True,
    "run the Sl gate at all (False = the pure-kr decompose path)",
    env="KR_GATE_BUCHI2LTL")

SL_MAX_STATES = OptionSpec(
    "portfolio.sl.max_states", 60,
    "skip the Sl gate on an input with more states than this",
    env="KR_GATE_MAX_STATES")

SL_VERIFY = OptionSpec(
    "portfolio.sl.verify", False,
    "opt-in audit: re-verify each adopted Sl formula against the node language",
    env="KR_GATE_VERIFY")

# The package's declared option set (the root builder aggregates these).
PORTFOLIO_OPTIONS = [SL_ENABLED, SL_MAX_STATES, SL_VERIFY]

__all__ = ["SL_ENABLED", "SL_MAX_STATES", "SL_VERIFY", "PORTFOLIO_OPTIONS"]
