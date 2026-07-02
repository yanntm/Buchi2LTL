# anchor — fixtures for the anchored SCC read-off

Hand-written HOA automata exercising `aut2ltl/anchor` (see its `algorithm.md`):
components whose phase is **anchored-recoverable** (anchors partition, loop letters
shared freely — preconditions P1 + P2) but **not input-deterministic** (the full
input labels `I(s)` overlap), so the loop-free read-off (algorithm.md Steps 1–2)
declines and only the anchored one applies. Unlike the sibling `hoa/<set>/`
folders, these are not generated from an `ltl/` list.

- `gafb_response.hoa` — the minimal DBA of `G(a → Fb)`; terminal SCC whose two
  states share the idle letter `!a & !b` on their self-loops. The `algorithm.md`
  worked example.
- `park_drop.hoa` — three-state terminal SCC where the park-subsumption drop
  fires: the sole accepting state has `L = A = a & b`, so its `F park` term is
  redundant and the built `fair` is the bare `GF(a & b)`; states 0 and 1 share
  the idle letter `!a & !b`, keeping the loop-free read-off out. (`gafb`'s park
  is the non-droppable contrast: `L(0) = !a | b ⊄ A(0) = b`.)
