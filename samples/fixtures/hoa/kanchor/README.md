# kanchor — fixtures for the graded (k-window) anchored read-off

Hand-written HOA automata exercising `aut2ltl/kanchor` (see its
`algorithm.md`): components whose phase is **not** recoverable from the last
letter (anchor's P1/P2 fail) but **is** recoverable from the last k adjacent
letters modulo stuttering. The k = 1 fixtures live in the sibling
`hoa/anchor/` folder — the rail probe (`tests/probes/kanchor_rail.py`) runs
kanchor against anchor on those and demands byte-identical labels.

- `gf_a_xa.hoa` — the minimal DBA of `GF(a & Xa)`, the `algorithm.md` worked
  example: k = 1 fails P1 (states 1 and 2 share the anchor `a`) and P2
  (state 2's loop `a` fires state 1's anchor); the pair windows partition,
  every sojourn collapses to `⊤`, the park drops by `Stay₂ = Enter₂`, and
  the label is exactly `GF(a & Xa)` with no simplifier involved.
