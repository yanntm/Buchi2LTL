"""
aut2ltl.partscc — the terminal-SCC partition leaf Translator.

A sibling of the translator engines (`aut2ltl.bls`, `aut2ltl.sl`) and the `inv`
decorator: `PartScc` labels a Language whose TGBA is a single terminal SCC by
partitioning its states into uniquely-characterizing entry classes and emitting one
validated `G(…)` formula — or declining. Defined entirely against the Translator
contract; imports only `spot`/`buddy` and the floor (`aut2ltl.language`,
`aut2ltl.result`).

Public entry: `PartScc`. See algorithm.md for the construction.
"""

from .partscc import PartScc

__all__ = ["PartScc"]
