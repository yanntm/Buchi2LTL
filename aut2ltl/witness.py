"""aut2ltl/witness.py — the non-LTL witness value type (a floor citizen).

When a language is not LTL-definable, the verdict can carry a *witness*: a finite
object exhibiting the counting that forbids LTL, checkable against the automaton.
`Witness` is that value — a pure data carrier with no engine dependency, so it sits
at the floor next to `LTLResult` and can be type-mentioned there. Producing one is a
separate, engine-side concern (`bls/definability/witness/extract_witness`); this
module only defines what is carried.

A witness is a counting family `(u, v, x, p)` with period `p > 1`: finite words `u`,
`v` and an ultimately-periodic tail `x = x_prefix . (x_cycle)^w` such that membership
of `u . v^n . x` toggles with `n mod p`. `v` is the period word (the group element),
`u` reaches a state where `v` acts with a non-trivial orbit, `x` discriminates the
phases. See `research_notes/non_ltl_certificates.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Witness:
    """Non-LTL witness material — the counting family `(u, v, x, p)`.

    `p` is the period (> 1); `v` is the period word (one concrete-letter string per
    step); `factor` is the 1-based generator-index word `v` lifts from (kept for
    checking the lift). `u` and the lasso tail `x = x_prefix . (x_cycle)^w` are the
    family completion (stage 2): membership of `u . v^n . x` toggles with `n mod p`.
    `u` / `x_*` are `None` until completed."""

    p: int
    v: List[str]
    factor: List[int]
    u: Optional[List[str]] = None
    x_prefix: Optional[List[str]] = None
    x_cycle: Optional[List[str]] = None

    def v_str(self) -> str:
        return " ; ".join(self.v)

    @property
    def complete(self) -> bool:
        return self.u is not None and self.x_cycle is not None

    def summary(self) -> str:
        """A human rendering of the counting family for a NOT_LTL diagnosis: the
        period, the toggling claim, and (when completed) the words `u`, `v`, `x`."""
        head = (f"witness: counting family, period p={self.p} — "
                f"u·vⁿ·x flips membership with n mod {self.p}")
        if not self.complete:
            return f"{head}\n    v = {self.v_str()}   (u, x not synthesised)"
        u = " ; ".join(self.u) if self.u else "ε"
        prefix = (" ; ".join(self.x_prefix) + " ; ") if self.x_prefix else ""
        x = f"{prefix}({' ; '.join(self.x_cycle or [])})ω"
        return f"{head}\n    u = {u} ;  v = {self.v_str()} ;  x = {x}"


__all__ = ["Witness"]
