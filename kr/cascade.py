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

    # Added for Phase A (LTL construction): letter data and original context
    aps: List[str] = field(default_factory=list)
    letter_masks: List[int] = field(default_factory=list)
    letter_valuations: List[Dict[str, bool]] = field(default_factory=list)
    original_aut: Any = None  # spot.twa_graph if available (for acc lifting)

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

    def num_letters(self) -> int:
        return len(self.generator_images)

    def move_config(self, config: Tuple[int, ...], letter_idx: int) -> Tuple[int, ...]:
        """Given a config (tuple of 1-based coords), return the next config under the given letter (0-based index into generators).

        Uses the original state mapping + generator images (lift via homomorphism).
        Assumes the decomposition provides a consistent covering.
        """
        if not self.state_to_config:
            raise ValueError("No state_to_config mapping available")
        if letter_idx < 0 or letter_idx >= len(self.generator_images):
            raise IndexError("letter_idx out of range")
        images = self.generator_images[letter_idx]
        # Find a representative original state for this config
        for s, c in self.state_to_config.items():
            if c == config:
                if s >= len(images):
                    raise ValueError(f"State {s} out of range for generator images")
                next_s = images[s]
                try:
                    return self.config_of(next_s)
                except KeyError:
                    raise ValueError(f"No config mapping for successor state {next_s}")
        raise ValueError(f"No original state found for config {config}")

    def top_of(self, config: Tuple[int, ...]) -> int:
        """Return the top-level (outermost, first) coordinate of the config."""
        return config[0] if config else 0

    def sub_config(self, config: Tuple[int, ...]) -> Tuple[int, ...]:
        """Return the lower sub-configuration (tail after the top coordinate). For level-0 this is ().
        This supports the inductive peeling for reachability formulas (top coord = current level's state).
        """
        return config[1:] if len(config) > 1 else ()

    def compute_stay_leave_from(self, config: Tuple[int, ...]) -> Dict[str, List[Tuple[int, Tuple[int, ...]]]]:
        """From this specific config (which encodes current top + current lower sub-config),
        partition the letters into those that keep the current top (stay) vs change it (leave).

        Returns {"stay": [(li, arrived_full_config), ...], "leave": [...] }
        These are the relevant combined letters <σ, current_lower> for building solid/dashed cases
        at this position. Derivable directly from move_config + generators (pure algebraic).
        """
        if not config:
            return {"stay": [], "leave": []}
        s = self.top_of(config)
        stay: List[Tuple[int, Tuple[int, ...]]] = []
        leave: List[Tuple[int, Tuple[int, ...]]] = []
        for li in range(self.num_letters()):
            try:
                nc = self.move_config(config, li)
                if self.top_of(nc) == s:
                    stay.append((li, nc))
                else:
                    leave.append((li, nc))
            except Exception:
                pass
        return {"stay": stay, "leave": leave}

    def compute_enters_to_from(self, config: Tuple[int, ...], target_top: int) -> List[Tuple[int, Tuple[int, ...]]]:
        """Letters from this config whose move changes top into exactly target_top (i.e. Enter for t from outside s).
        Used for the dashed-arrow (change top) case in reachability.
        """
        if not config:
            return []
        enters: List[Tuple[int, Tuple[int, ...]]] = []
        curr_top = self.top_of(config)
        if curr_top == target_top:
            return enters  # already there, not "enter"
        for li in range(self.num_letters()):
            try:
                nc = self.move_config(config, li)
                if self.top_of(nc) == target_top:
                    enters.append((li, nc))
            except Exception:
                pass
        return enters

    def all_top_values(self) -> List[int]:
        """All distinct top-coordinate values appearing in configs (for level of these configs)."""
        return sorted({self.top_of(c) for c in self.all_configs()})

    def all_configs(self) -> List[Tuple[int, ...]]:
        """Return sorted list of distinct configurations that appear in the mapping."""
        return sorted(set(self.state_to_config.values()))

    def build_config_transitions(self) -> Dict[Tuple[int, ...], Dict[int, Tuple[int, ...]]]:
        """Build a simple transition table: config -> {letter_idx: next_config} for all letters and appeared configs.

        This is the core 'configuration automaton' transition relation (unlabeled for now; use letter_valuations for guards).
        """
        trans: Dict[Tuple[int, ...], Dict[int, Tuple[int, ...]]] = {}
        configs = self.all_configs()
        for c in configs:
            trans[c] = {}
            for li in range(self.num_letters()):
                try:
                    trans[c][li] = self.move_config(c, li)
                except Exception:
                    # If some config not fully covered, leave missing
                    pass
        return trans

    def build_configuration_automaton(self):
        """Return a lightweight structure representing the automaton on configurations.

        states: list of config tuples (the appeared ones)
        transitions: dict config -> list of (letter_idx, next_config, valuation_dict)
        aps, letter_valuations available on self.
        This is the object on which we will run the inductive reachability from the paper.
        """
        states = self.all_configs()
        trans_table = self.build_config_transitions()
        transitions = {}
        for c in states:
            transitions[c] = []
            for li in range(self.num_letters()):
                if li in trans_table.get(c, {}):
                    nc = trans_table[c][li]
                    val = self.letter_valuations[li] if li < len(self.letter_valuations) else {}
                    transitions[c].append((li, nc, val))
        return {
            "states": states,
            "aps": self.aps,
            "num_letters": self.num_letters(),
            "transitions": transitions,
            "state_to_config_orig": self.state_to_config,  # for lifting acc later
        }

    def accepting_configs(self) -> set:
        """Lift of 'accepting' configs from the (completed det parity) automaton.

        A config is considered 'accepting' (heuristic) if at least one state
        mapped to it has an outgoing transition carrying a non-empty acc mark
        (i.e. a priority for parity). For parity automata this is a coarse
        over-approximation: acceptance is defined by the liminf/limsup parity
        of priorities seen along infinite runs (per aut.get_acceptance()),
        not per-state or simple Inf marks. The heuristic is kept for the
        current 'infinitely often reach acc-config' builder framing.

        Since the input is normalized by Spot to a deterministic complete
        minimized parity automaton, all states (including any sinks added
        for completeness) are ordinary; handled uniformly by reachability.
        """
        if self.original_aut is None:
            # Fallback: assume no acc info
            return set()
        aut = self.original_aut
        acc_configs = set()
        acc_cond = str(aut.get_acceptance()).strip().lower()
        if acc_cond in ("t", "true", "1") or acc_cond == "0 t":
            # Tautological acceptance (e.g. "true" formula under parity): all states/configs count.
            return set(self.state_to_config.values())
        if acc_cond in ("f", "false", "0 f"):
            return set()
        for s, c in self.state_to_config.items():
            try:
                for e in aut.out(s):
                    if e.acc and list(e.acc.sets()):  # has some acc mark (priorities for parity, Inf for Buchi)
                        acc_configs.add(c)
                        break
            except Exception:
                # out of range etc: skip
                pass
        return acc_configs


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
