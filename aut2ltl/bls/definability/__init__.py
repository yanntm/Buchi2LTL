"""
aut2ltl.bls.definability — the LTL-definability decision for a `Language`.

LTL == star-free == counter-free == the deterministic transition monoid is
APERIODIC. This package decides that one question and caches it on the Language,
so the cascade — which is *unsound* on a non-aperiodic language — gates its build
on it and reports NOT_LTL instead of constructing a wrong formula.

Public entry: `label_ltl_definable`. See algorithm.md for the algebra (the
aperiodicity characterization, the sbacc trap, the conclusiveness/SAT-min rule,
and fail-open). The GAP scripts it drives stay in `bls/gap/`; the Spot→generator
extraction stays in `bls/extract.py` (both shared with the cascade's holonomy).
"""

from .tester import label_ltl_definable

__all__ = ["label_ltl_definable"]
