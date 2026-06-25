"""aut2ltl.spotrun — the single seam for formula -> automaton translation.

`translate` is the one place the construction turns a formula into an automaton,
so the policy for how that heavy Spot call runs lives here rather than inlined at
the call site (see README.md). Today it is a transparent pass-through to Spot's
in-process binding; the size guard and the wall-time-bounded `ltl2tgba` backend
layer on top without changing this contract.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import spot

__all__ = ["translate"]


def translate(f: "spot.formula") -> "spot.twa_graph":
    """Translate `f` to an automaton — the single mediated Spot translate.

    Currently a direct pass-through to the in-process binding (`f.translate()`).
    The isolation policy (size guard, killable wall-time bound) is layered on
    later without changing this signature."""
    return f.translate()
