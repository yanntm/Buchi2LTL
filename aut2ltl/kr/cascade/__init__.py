"""
aut2ltl.kr.cascade — the Krohn-Rhodes cascade data model and its analysis.

`model.py` holds the `Cascade` (levels, state↔config, letter valuations,
`move_config`, Enter/Stay/Leave helpers) and `LevelInfo` / `Config`. The
graph-theoretic analysis on the configuration automaton — reachable/accepting
configs, the pruned config twa, the good Müller sets — lives in `config_graph.py`
(a pure leaf: it takes a `Cascade` and never imports back into the engine).

Re-exported here so callers use `aut2ltl.kr.cascade` as one module.
"""

from .model import Cascade, LevelInfo, Config, make_trivial_cascade
from .holder import CascadeHolder
from .config_graph import (
    build_pruned_config_aut,
    reachable_configs,
    good_muller_sets,
)

__all__ = [
    "Cascade",
    "CascadeHolder",
    "LevelInfo",
    "Config",
    "make_trivial_cascade",
    "build_pruned_config_aut",
    "reachable_configs",
    "good_muller_sets",
]
