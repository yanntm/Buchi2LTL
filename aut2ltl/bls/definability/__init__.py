"""
aut2ltl.bls.definability — the LTL-definability decision for a `Language`.

LTL == star-free == counter-free == the deterministic transition monoid is
APERIODIC. This package decides that one question and caches it on the Language,
so the cascade — which is *unsound* on a non-aperiodic language — gates its build
on it and reports NOT_LTL instead of constructing a wrong formula.

Public entries: `label_ltl_definable` (the raw verdict oracle — the `tester/`
peer) and `definability_gate` (the border decorator that wraps a translator,
reports NOT_LTL with a diagnosis and a knob-guarded witness on the non-definable
branch, and delegates otherwise). See tester/algorithm.md for the algebra (the
aperiodicity characterization, the sbacc trap, the conclusiveness/SAT-min rule,
the absorbing NOT_LTL verdict, and the abstain rule when the oracle can't run).
The GAP scripts it drives stay in `bls/gap/`; the Spot→generator extraction stays
in `bls/extract.py` (both shared with the cascade's holonomy).
"""

from .tester import label_ltl_definable
from .gate import definability_gate

__all__ = ["label_ltl_definable", "definability_gate"]
