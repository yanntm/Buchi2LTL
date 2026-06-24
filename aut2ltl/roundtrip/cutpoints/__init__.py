"""
aut2ltl.roundtrip.cutpoints — Finder strategies for roundtrip's Φ (see algorithm.md).

Each finder satisfies the `Finder` contract (`Formula → Node | None`) of
`aut2ltl/roundtrip/finder.py`, locating the node roundtrip cuts.

Public entries: `root`, `toplevel`.
"""

from .root import root
from .toplevel import toplevel

__all__ = ["root", "toplevel"]
