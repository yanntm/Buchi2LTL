# aut2ltl.bls.cascade — the cascade data model + analysis

This package holds the Krohn–Rhodes **cascade** that the decomposition produces
and everything that reads its structure. It is the data layer the translator
members consume; it builds no LTL itself.

## Modules

- **`model.py`** — `Cascade` plus `LevelInfo` and `Config`. A `Cascade` is the
  reset cascade of the normalized deterministic automaton `D`: the levels, the
  state↔config maps (1-based holonomy coordinates), the per-letter valuations,
  `move_config` (the transition table), the Enter/Stay/Leave letter partitions,
  and `original_aut` (the authoritative `D`). The graph-analysis methods on
  `Cascade` are thin delegations to `config_graph`.

- **`config_graph.py`** — analysis on the configuration automaton, as pure
  functions of a `Cascade` (it imports nothing from the engine, so it stays a
  leaf): reachable configs, accepting / Büchi-accepting / coBüchi-finite config
  sets, the pruned config twa, basins, and `good_muller_sets` — the recurrent
  config families the BLS Muller assembly (`kr/muller.py`) consumes.

## Layering

`config_graph` depends only on a `Cascade` (+ Spot); `model` delegates its
analysis to `config_graph`. Nothing here imports the formula-construction core
(`reachability_operators`, `fin`, `ltl_builders`, `muller`) — construction sits
*above* this package. `from aut2ltl.bls.cascade import Cascade, good_muller_sets,
…` is the public surface (re-exported in `__init__.py`).
