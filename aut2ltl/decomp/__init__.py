"""
aut2ltl.decomp — the (de)composition approaches.

A theme folder, one self-contained subpackage per way of breaking a language into
easier pieces and stitching the pieces' labels back together. Each is an independent
peer with its own `algorithm.md`; nothing here is shared by force — grouping is by
theme, not by a common base. This `__init__` deliberately imports none of them, so
pulling in one approach drags in neither its siblings nor their dependencies.

- `decomp.scc`        — `SccDecompose`: ∨ over accepting SCCs.
- `decomp.strength`   — `StrengthDecompose`: ∨ over weak/terminal/strong strengths.
- `decomp.acceptance` — `AccDecompose`: ∧ over acceptance conjuncts (deterministic).
- `decomp.inv`        — `Invariant`: factor a safety invariant out of the suffix.

Import the approach you want directly, e.g. `from aut2ltl.decomp.scc import
SccDecompose`.
"""
