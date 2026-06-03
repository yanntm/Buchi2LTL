"""
Lightweight representation of a holonomy (Krohn-Rhodes) cascade produced by SgpDec.

This is the Python-side bridge object that the rest of the pipeline (and future
LTL synthesis) will consume. It is intentionally simple and serializable.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class LevelInfo:
    """Description of one level in the cascade."""
    index: int
    size: int
    # "reset", "group", "constant", "unknown", etc. (we parse what SgpDec gives us)
    kind: str = "unknown"
    # Extra metadata if SgpDec provides it (e.g. group structure "C2", "S3", ...)
    structure: Optional[str] = None


@dataclass
class Cascade:
    """
    Structured result of a holonomy decomposition.

    Attributes
    ----------
    num_levels : int
        Number of levels in the cascade (depth of the hierarchical decomposition).
    levels : list[LevelInfo]
        Per-level information (size, kind, ...). Length == num_levels.
    num_states : int
        Number of states in the *original* transformation semigroup / automaton.
    state_to_config : dict[int, tuple[int, ...]]
        Mapping from original state index (0-based) to its coordinate tuple in the
        cascade (one coordinate per level). The length of each tuple == num_levels.
        Coordinates are usually 1-based as emitted by SgpDec; we keep them as-is.
    config_to_state : dict[tuple[int, ...], int]
        Reverse mapping (best effort; may not be unique in some degenerate cases).
    generator_images : list[list[int]]
        The original generators we fed to SgpDec (for round-tripping / debugging).
        Each inner list is the image list for one generator: images[q] = delta(q, gen).
    raw_output : str
        The complete stdout captured from the GAP run (for debugging / auditing).
    metadata : dict
        Any extra info we captured (e.g. "skeleton_depth", warnings, timing).
    """

    num_levels: int
    levels: List[LevelInfo] = field(default_factory=list)
    num_states: int = 0
    state_to_config: Dict[int, Tuple[int, ...]] = field(default_factory=dict)
    config_to_state: Dict[Tuple[int, ...], int] = field(default_factory=dict)
    generator_images: List[List[int]] = field(default_factory=list)
    raw_output: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.levels and len(self.levels) != self.num_levels:
            # Allow caller to pass partial levels; we still trust num_levels.
            pass
        # Ensure configs are tuples (hashable)
        self.state_to_config = {
            int(k): tuple(int(x) for x in v) if not isinstance(v, tuple) else v
            for k, v in self.state_to_config.items()
        }
        self.config_to_state = {
            (tuple(int(x) for x in k) if not isinstance(k, tuple) else k): int(v)
            for k, v in self.config_to_state.items()
        }

    def config_of(self, state: int) -> Tuple[int, ...]:
        return self.state_to_config[state]

    def state_of(self, config: Tuple[int, ...]) -> Optional[int]:
        return self.config_to_state.get(config)

    def is_trivial(self) -> bool:
        """True if the cascade has a single level of size 1 (or equivalent)."""
        return self.num_levels <= 1 and all(l.size <= 1 for l in self.levels)

    def has_nontrivial_groups(self) -> bool:
        """Heuristic: any level whose kind mentions a non-trivial group structure."""
        for lv in self.levels:
            if lv.kind and "group" in lv.kind.lower():
                return True
            if lv.structure and lv.structure not in ("1", "C1", "trivial"):
                return True
        return False

    def summary(self) -> str:
        lv_str = ", ".join(f"L{i}:{lv.size}{('('+lv.structure+')' if lv.structure else '')}"
                           for i, lv in enumerate(self.levels))
        return (f"Cascade(n_states={self.num_states}, levels={self.num_levels} "
                f"[{lv_str}])")

    def __repr__(self) -> str:
        return self.summary()


def make_trivial_cascade(n_states: int = 1) -> Cascade:
    """Factory for the degenerate 0- or 1-state case (useful for tests)."""
    return Cascade(
        num_levels=1,
        levels=[LevelInfo(index=0, size=n_states, kind="reset")],
        num_states=n_states,
        state_to_config={s: (s+1,) for s in range(n_states)},  # 1-based convention
        config_to_state={(s+1,): s for s in range(n_states)},
    )
