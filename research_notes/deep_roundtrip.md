# Deep round trip — collapsing buchi towers from the leaves

*A research note — the 2026-06-24 experiments behind `deep_roundtrip` / `deep_nobls`.*

## 1. The question

A round trip (formula → automaton → formula) often returns a *smaller* formula.
But on a blown-up result the **root is over the translate bound**, so a top-level
round trip cannot even start. Question: are there **sub-DAG nodes** whose language
is recoverable *and* comes back smaller — so we could reduce bottom-up and let the
whole tower collapse?

## 2. The probe

`tests/probes/roundtrip/probe_shared_nodes.py` (any HOA):

1. build F via a recipe (default = the `default` portfolio), read its hash-consed DAG;
2. pick nodes with **>1 parent** (shared); per node compute **sharing = #root→node
   paths** (memoized) + size + translatability (`Language._guard_translation`, same
   constants as `Language.of`);
3. **dance** each shared node under the translate bound: round-trip via `survey`
   (`--no-verify`, severe SIGKILL); selectable dance recipe (`default` / `nobls` / …).
   Same-size and declined outcomes are aggregated (count + time); only size-changes
   and timeouts print, blowups dumped with formula + technique.

## 3. What we found (aut_10380, default F = 1704 DAG nodes)

- 463 shared nodes; 116 translatable at the default bound, 347 too large.
- Dance under **default**: 38 smaller, 50 same, **21 severe blowups**, 7 timeout.
  *Every* severe blowup (×24…×1247; a 14-node U-language → 10912 nodes) was a
  **`buchi`** answer. The daisy/partscc/inv layers gave all the compact (shrinking)
  forms, cheaply (~0.11 s vs 1–4 s for the buchi blobs).
- **buchi (the bls cascade) is the sole blob factory.** This motivated `nobls`
  (`portfolio/recipes/nobls.py`): the full decomposition over `daisy_trio_det_inv`
  floored on `PartScc` *alone* — declines where only the cascade could answer.
- Dance under **nobls**: the 38 shrinks + 50 same are unchanged, the 21 blowups
  become clean **declines**, 0 timeouts, 5.5× less time. No buchi ⇒ no blowups.

## 4. Why `deep_roundtrip` / `deep_nobls`

The shrinks are *internal* and shared, which the top-level `roundtrip_decomp`
(cut at `toplevel(And)`) cannot reach. `aut2ltl/roundtrip_deep/` adds
`deep_roundtrip(R)`: a finder-free **bottom-up memoized catamorphism** — re-present
every node from its already-re-presented children, one post-order pass, memoized on
formula identity (DAG-complexity; correctness free from the single hash-consed DAG).
`deep_nobls` = `cakedsdet` seed + `deep_roundtrip(best_of([identity, relabel(nobls)]))`,
`Simplify`-wrapped. Two labelers sit in the already-separate slots (seed = forward,
`relabel` = return); **no edit to `roundtrip` needed**.

## 5. Current limits

- aut_10380 collapse curve: default **1704** → deep@tree100 **1470** (−14%) →
  deep@tree1000 **1189** (−30%, 6.4 s). Propagation compounds bottom-up.
- **Raising the *tree* (flat-size) bound is safe; raising *temporal* past 32 is not**
  — temporal>32 ⇒ >32 acceptance sets ⇒ spot runs wild (uncatchable hang). The
  temporal=32 guard is what "catches" it (refuses pre-call).
- Probe sweep (temporal=32): translatable 116→164 as tree 100→1000, +18 shrinks,
  saturating by ~300–1000; the residual ~300 skipped nodes are temporal>32 — the
  real acceptance ceiling.
- **deep_nobls in-process ceiling ≈ tree=1000.** At tree=1500 a single node's
  `translate` becomes pathologically slow, and the *in-process* fold cannot kill a
  signal-deaf spot call → the whole fold hangs (SIGKILL). The probe survives high
  limits only because it dances each node in a *subprocess* with a per-node SIGKILL.

## 6. Next lever

Not a bigger constant — a **per-translate external timeout** (the `proc.py` /
bounded-`ltl2tgba`-subprocess idea): bound each node-translate (~2–3 s, killable) so
a slow node *declines* instead of hanging the fold, letting the tree ceiling rise
freely. Then revisit how far the tower collapses.
