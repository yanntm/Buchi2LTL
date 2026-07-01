"""aut2ltl/witness.py — the non-LTL witness value type (a floor citizen).

When a language is not LTL-definable, the verdict can carry a *witness*: a finite
object exhibiting the counting that forbids LTL, checkable against the automaton.
`Witness` is that value — a pure data carrier with no engine dependency, so it sits
at the floor next to `LTLResult` and can be type-mentioned there. Producing one is a
separate, engine-side concern (`bls/definability/witness/extract_witness`); this
module only defines what is carried.

A witness is a counting family with period `p > 1`, in one of two shapes (see
`bls/definability/witness/algorithm.md` for why two are needed and suffice):

  * linear   — `(u, v, x, p)`: membership of `u . v^n . x` toggles with `n mod p`,
    `x = x_prefix . (x_cycle)^w` an ultimately-periodic tail;
  * ω-power  — `(u, v, y, p)`: membership of `u . (v^n . y)^w` toggles with
    `n mod p`, the period riding INSIDE the lasso cycle (the only shape that can
    witness a prefix-independent language).

`v` is the period word (the group element), `u` reaches a state where `v` acts
with a non-trivial orbit, `x` (or the loop tail `y`) discriminates the phases.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Witness:
    """Non-LTL witness material — a counting family in one of two shapes.

    `p` is the period (> 1); `v` is the period word (one concrete-letter string per
    step); `factor` is the 1-based generator-index word `v` lifts from (kept for
    checking the lift). The completion is one of:

      * linear  — `u` and the lasso tail `x = x_prefix . (x_cycle)^w`:
        membership of `u . v^n . x` toggles with `n mod p`;
      * ω-power — `u` and the loop tail `y`:
        membership of `u . (v^n . y)^w` toggles with `n mod p`.

    All completion fields are `None` until completed; at most one shape is filled."""

    p: int
    v: List[str]
    factor: List[int]
    u: Optional[List[str]] = None
    x_prefix: Optional[List[str]] = None
    x_cycle: Optional[List[str]] = None
    y: Optional[List[str]] = None

    def v_str(self) -> str:
        return " ; ".join(self.v)

    def prepend(self, word: str) -> "Witness":
        """Prepend a finite word (Spot syntax, `;`-separated letters) to `u`, the
        anchor prefix, and return self.

        The lift a *peeler* applies on the way up: a translator that consumed a
        prefix before reaching the NOT_LTL core gets a child witness whose `u`
        reaches the orbit from that core, not from the host's initial state.
        Prefixing the consumed word re-anchors the family over the host's own input.
        `v`/`x` are untouched — the peel re-roots, it does not relabel, so the period
        and the discriminating tail stay valid over the same alphabet. A no-op on `u`
        when the family is incomplete (`u is None`): there is no anchor to lift, and
        the incompleteness stands on its own."""
        if self.u is not None:
            letters = [t.strip() for t in word.split(";") if t.strip()]
            self.u = letters + self.u
        return self

    @property
    def omega_power(self) -> bool:
        """True when the completion is the ω-power shape (`y` filled)."""
        return self.y is not None

    @property
    def complete(self) -> bool:
        return self.u is not None and (self.x_cycle is not None or self.y is not None)

    def summary(self) -> str:
        """A human rendering of the counting family for a NOT_LTL diagnosis: the
        period, the toggling claim (per shape), and the completed words. ASCII
        only (the serialized form is the machine channel)."""
        if self.omega_power:
            head = (f"witness: counting family, period p={self.p} -- "
                    f"u.(v^n.y)^w flips membership with n mod {self.p}")
            u = " ; ".join(self.u) if self.u else "[]"
            y = " ; ".join(self.y or [])
            return f"{head}\n    u = {u} ;  v = {self.v_str()} ;  y = {y}"
        head = (f"witness: counting family, period p={self.p} -- "
                f"u.v^n.x flips membership with n mod {self.p}")
        if not self.complete:
            return f"{head}\n    v = {self.v_str()}   (u, x not synthesised)"
        u = " ; ".join(self.u) if self.u else "[]"
        prefix = (" ; ".join(self.x_prefix) + " ; ") if self.x_prefix else ""
        x = f"{prefix}({' ; '.join(self.x_cycle or [])})^w"
        return f"{head}\n    u = {u} ;  v = {self.v_str()} ;  x = {x}"

    # ----------------------------------------------------------------------- #
    # Machine round-trip: a single ASCII line in Spot word syntax. The inverse
    # pair (`serialize` / `parse`) is what lets the front end emit the witness
    # and a downstream verifier replay it; `factor` is internal (the generator-
    # index lift) and not carried — `parse` reconstructs with `factor=[]`.
    # ----------------------------------------------------------------------- #
    def serialize(self) -> str:
        """The compact one-line payload — linear `p=3 u=[] v=[a; a] x=[cycle{!a}]`,
        ω-power `p=2 u=[] v=[a] y=[!a]` (the sampled word is `u.(v^n.y)^w`).

        Bare (no `NOT_LTL` tag): the front end prefixes the result kind, symmetric
        with a bare LTL formula. Words use Spot syntax: a finite word is `l; l`, the
        lasso tail `x` is `prefix; cycle{l; l}`. An incomplete family (no `u`/`x`/`y`)
        drops them and is flagged `incomplete`."""
        v = f"v=[{'; '.join(self.v)}]"
        if not self.complete:
            return f"p={self.p} {v} incomplete"
        u = f"u=[{'; '.join(self.u or [])}]"
        if self.omega_power:
            return f"p={self.p} {u} {v} y=[{'; '.join(self.y or [])}]"
        prefix = ("; ".join(self.x_prefix) + "; ") if self.x_prefix else ""
        x = f"x=[{prefix}cycle{{{'; '.join(self.x_cycle or [])}}}]"
        return f"p={self.p} {u} {v} {x}"

    @staticmethod
    def parse(line: str) -> "Witness":
        """Inverse of `serialize`: rebuild a `Witness` from its one-line form.

        Tolerates the leading `NOT_LTL` tag. Raises `ValueError` if `p`/`v` are
        absent. The `incomplete` form (or a missing `u`/`x`/`y`) yields a witness
        with the completion left None. `factor` is not recoverable from the line and
        is set empty (it is only used to re-check the generator lift, not to replay)."""
        def _letters(body: str) -> List[str]:
            return [t.strip() for t in body.split(";") if t.strip()]

        m_p = re.search(r"\bp=(\d+)", line)
        m_v = re.search(r"\bv=\[([^\]]*)\]", line)
        if m_p is None or m_v is None:
            raise ValueError(f"not a witness line (need p= and v=): {line!r}")
        p = int(m_p.group(1))
        v = _letters(m_v.group(1))

        m_u = re.search(r"\bu=\[([^\]]*)\]", line)
        m_y = re.search(r"\by=\[([^\]]*)\]", line)
        if m_u is not None and m_y is not None and "incomplete" not in line:
            return Witness(p=p, v=v, factor=[], u=_letters(m_u.group(1)),
                           y=_letters(m_y.group(1)))
        m_x = re.search(r"\bx=\[([^\]]*)\]", line)
        if "incomplete" in line or m_u is None or m_x is None:
            return Witness(p=p, v=v, factor=[])

        u = _letters(m_u.group(1))
        x_body = m_x.group(1)
        m_cyc = re.search(r"cycle\{([^}]*)\}", x_body)
        if m_cyc is None:
            raise ValueError(f"x has no cycle{{...}}: {line!r}")
        x_cycle = _letters(m_cyc.group(1))
        x_prefix = _letters(x_body[: m_cyc.start()])
        return Witness(p=p, v=v, factor=[], u=u, x_prefix=x_prefix, x_cycle=x_cycle)


__all__ = ["Witness"]
