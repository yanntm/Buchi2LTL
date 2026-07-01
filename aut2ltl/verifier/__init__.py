"""aut2ltl.verifier — the standalone non-LTL witness checker.

A `NOT_LTL` verdict can carry a `Witness` — a counting family, linear
(`u . v^n . x` toggling with `n mod p`) or ω-power (`u . (v^n . y)^w` toggling with
`n mod p`). This package replays that family against the input automaton by
membership — independent of the engine that produced the verdict,
acceptance-agnostic (Spot membership only), floor-level.

Three ways in: the API (`verify(aut, witness) -> (ok, pattern)`), the
boundary-crossing filter (`revalidated(result, lang)` — keep a NOT_LTL only if its
family replays against `lang`), and the CLI (`python3 -m aut2ltl.verifier INPUT
"NOT_LTL p=3 u=[] v=[a; a] x=[cycle{!a}]"`).
"""
from __future__ import annotations

from .check import member, verify, verify_omega, verify_suggestive, verify_with
from .revalidate import revalidated, revalidated_by_parts

__all__ = ["member", "verify", "verify_omega", "verify_suggestive", "verify_with",
           "revalidated", "revalidated_by_parts"]
