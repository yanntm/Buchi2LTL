"""
bls/cascade/holder.py — CascadeHolder: a pure Cascade plus its per-build caches.

The CascadeTranslator members and the recursive reachability core need somewhere
to memoize subproblems and count distinct expansions for the duration of ONE
construction. Rather than module-global memos plus a reset band-aid (the old
`reachability_operators` globals + `reset_build_state`), that build state lives
here, on a lightweight wrapper created once per construction (in `bls/aut2cas.py`)
and threaded as the CascadeTranslator input. A fresh holder IS a fresh build: no
reset call, and the memo lifetime equals the holder's — so the previous
`id(casc)`-reuse hazard (a recycled id returning another build's cached formulas)
is gone by construction.

The wrapper is transparent: `__getattr__` delegates every Cascade attribute and
method to the wrapped `cascade`, so the construction code keeps reading
`casc.move_config(...)`, `casc.num_levels`, `casc.all_configs()`, etc. unchanged
while the holder owns `reach_memo` / `helper_memo` / `uncond_memo` and the
`reach_calls` / `fin_calls` counters as its own fields. The `Cascade` itself is
never touched (it stays a pure data model).
"""
from __future__ import annotations

from typing import Any, Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import spot
    from .model import Cascade


class CascadeHolder:
    """A `Cascade` plus the mutable caches/counters of one construction.

    Delegates all `Cascade` attributes to `self.cascade` (so it stands in for the
    cascade everywhere the construction reads it) while owning the per-build memos
    and counters. One holder per construction; discard it to reset the build."""

    def __init__(self, cascade: "Cascade") -> None:
        self.cascade: "Cascade" = cascade
        # reach_strong memo: key (S, B, beta_f, T, tau_f, level) -> formula.
        self.reach_memo: Dict[Tuple[Any, ...], "spot.formula"] = {}
        # helper memo (solid/wsolid/dashed + the >0 cores), keyed by the decorator.
        self.helper_memo: Dict[Tuple[Any, ...], "spot.formula"] = {}
        # fin.py _uncond_reach_strict memo.
        self.uncond_memo: Dict[Any, "spot.formula"] = {}
        # Distinct reach_strong expansions: the runaway-guard counter AND the
        # profiling metric. Distinct fin_c calls: a smaller independent guard.
        self.reach_calls: int = 0
        self.fin_calls: int = 0

    def __getattr__(self, name: str) -> Any:
        # Reached only for attributes NOT set on the holder itself; delegate to
        # the wrapped cascade. `cascade` is guarded to avoid infinite recursion
        # if it is queried before __init__ has set it.
        if name == "cascade":
            raise AttributeError(name)
        return getattr(self.cascade, name)

    def __repr__(self) -> str:
        return f"CascadeHolder({self.cascade!r}, reach_calls={self.reach_calls})"


__all__ = ["CascadeHolder"]
