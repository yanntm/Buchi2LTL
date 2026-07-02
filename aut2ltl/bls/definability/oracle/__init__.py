"""aut2ltl.bls.definability.oracle — the exact LTL-definability decision.

Computes the syntactic ω-semigroup of the language as a quotient of the
acceptance-enriched monoid and reads aperiodicity off it: **LTL** and
**NOT_LTL** (with a replayed counting family) are both theorems, and
**INCONCLUSIVE** is only ever a resource cap. See `algorithm.md` for the
construction and `decide` for the entry point.
"""
from .oracle import INCONCLUSIVE, LTL, NOT_LTL, OracleVerdict, decide

__all__ = ["decide", "OracleVerdict", "LTL", "NOT_LTL", "INCONCLUSIVE"]
