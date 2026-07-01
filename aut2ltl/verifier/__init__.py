"""aut2ltl.verifier — the standalone non-LTL witness checker.

A `NOT_LTL` verdict can carry a `Witness` (a counting family `(u, v, x, p)`). This
package replays that family against the input automaton by membership and reports
whether `u . v^n . x` toggles with `n mod p` — independent of the engine that
produced the verdict, acceptance-agnostic (Spot membership only), floor-level (it
depends on nothing but `Witness` and Spot).

Usable two ways: as an API (`verify(aut, witness) -> (ok, pattern)`) for any caller
that wants to re-check or iterate witnesses, and as a CLI (`python3 -m aut2ltl.verifier
INPUT "NOT_LTL p=3 u=[] v=[a; a] x=[cycle{!a}]"`).
"""
from __future__ import annotations

from .check import member, verify, verify_omega, verify_suggestive

__all__ = ["member", "verify", "verify_omega", "verify_suggestive"]
