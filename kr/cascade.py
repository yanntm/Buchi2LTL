"""
Lightweight representation of a holonomy (Krohn-Rhodes) cascade produced by SgpDec.

This is the Python-side bridge object that the rest of the pipeline (and future
LTL synthesis) will consume. It is intentionally simple and serializable.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, NamedTuple, FrozenSet

class Config(NamedTuple):
    """Ref-style cascade configuration (tuple of per-level states). Hashable, explicit empty for level 0."""
    states: Tuple[int, ...]

    def __repr__(self) -> str:
        return f"Config{self.states}"


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

    # Added for Phase A (LTL construction): letter data and the (normalized) det aut context.
    # The stored aut is the deterministic complete parity version produced by
    # decompose_aut; this *is* the authoritative D for the algorithm (configs,
    # h via state_to_config, acc lifting, reachability, Fin, assembly).
    # Callers keep any pre-norm aut aside only for their own final equiv check.
    aps: List[str] = field(default_factory=list)
    letter_masks: List[int] = field(default_factory=list)
    letter_valuations: List[Dict[str, bool]] = field(default_factory=list)
    original_aut: Any = None  # the normalized det parity aut (our working D)

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
        """True if any level's kind or structure indicates a non-trivial group (vs pure reset/constant)."""
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

    # --- Refined Cascade API (architectural adoption from reference.md item 2) ---
    # Backward-compatible extension: adds explicit sigma, combined letters,
    # first-class stay/enter/leave returning lists of cl tuples (for literal paper disjuncts
    # in Rs0/Rc0 etc.), and Config NamedTuple (hashable, 0-config explicit).
    # Existing move_config / compute_* / top_of remain for compat.
    # This reduces impedance mismatch for exact R4/R5 impls.

    @property
    def sigma(self) -> List[FrozenSet]:
        """List of letters as frozensets of true APs (ref-style Σ)."""
        return [frozenset(k for k, v in val.items() if v) for val in self.letter_valuations]

    def combined_letters(self, level_idx: int) -> List[Tuple]:
        """For level, list of possible combined cl = (sig_frozenset, lower_tuple).
        Used to make paper disjuncts literal."""
        if level_idx < 0 or level_idx >= self.num_levels:
            return []
        # Collect from reachable configs at this level
        cls = set()
        for c in self.all_configs():
            if len(c) <= level_idx:
                continue
            # For each letter from a rep at this level's state
            s = c[level_idx]
            for li in range(self.num_letters()):
                try:
                    nc = self.move_config(c, li)
                    if nc[level_idx] == s:  # stay for this level's top? Wait, for general need care
                        sig = self.sigma[li]
                        lower = nc[level_idx+1:] if level_idx+1 < len(nc) else ()
                        cls.add( (sig, lower) )
                except:
                    pass
        return list(cls)

    def stay(self, level_idx: int, state: int) -> List[Tuple]:
        """Ref-style: combined letters that keep 'state' fixed at this level.
        Returns list of (sig_frozenset, lower_tuple) for direct use in Rs0 etc."""
        res = []
        for c in self.all_configs():
            if len(c) <= level_idx or c[level_idx] != state:
                continue
            for li in range(self.num_letters()):
                try:
                    nc = self.move_config(c, li)
                    if nc[level_idx] == state:
                        sig = self.sigma[li]
                        lower = nc[level_idx+1:] if level_idx+1 < len(nc) else ()
                        res.append( (sig, lower) )
                except:
                    pass
        # dedup
        return list(set(res))

    def enter(self, level_idx: int, target_state: int) -> List[Tuple]:
        """Ref-style Enter for target_state at level. List of (sig, lower) that reset to it."""
        res = []
        for c in self.all_configs():
            if len(c) <= level_idx or c[level_idx] == target_state:
                continue
            for li in range(self.num_letters()):
                try:
                    nc = self.move_config(c, li)
                    if nc[level_idx] == target_state:
                        sig = self.sigma[li]
                        lower = nc[level_idx+1:] if level_idx+1 < len(nc) else ()
                        res.append( (sig, lower) )
                except:
                    pass
        return list(set(res))

    def leave(self, level_idx: int, state: int) -> List[Tuple]:
        """Ref-style Leave from state at level."""
        st = set(self.stay(level_idx, state))
        all_cl = self.combined_letters(level_idx)
        return [cl for cl in all_cl if cl not in st]

    # Config factory for ref-style
    def make_config(self, states: Tuple[int, ...]) -> Config:
        return Config(states)

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

    # ------------------------------------------------------------------
    # Config-graph analysis (reachability, pruned config aut, accepting
    # configs, good Muller sets, basins) lives in kr/config_graph.py.
    # Thin delegating methods below keep all call sites unchanged.
    # ------------------------------------------------------------------

    def accepting_configs(self) -> set:
        """Configs from which accepting infinite runs can recur (w.r.t. our D).
        See config_graph.accepting_configs."""
        from . import config_graph as _cg
        return _cg.accepting_configs(self)

    def summary(self) -> str:
        lv_str = ", ".join(f"L{i}:{lv.size}{('('+lv.structure+')' if lv.structure else '')}"
                           for i, lv in enumerate(self.levels))
        return (f"Cascade(n_states={self.num_states}, levels={self.num_levels} "
                f"[{lv_str}])")

    def __repr__(self) -> str:
        return self.summary()

    def reachable_configs(self) -> list:
        """BFS from the initial config. See config_graph.reachable_configs."""
        from . import config_graph as _cg
        return _cg.reachable_configs(self)

    def build_pruned_config_aut(self):
        """Pruned config twa with acc lifted from D. See config_graph.build_pruned_config_aut."""
        from . import config_graph as _cg
        return _cg.build_pruned_config_aut(self)

    def compute_good_muller_sets(self):
        """Good Muller sets M on configs (strongly-connected accepting subsets of
        non-rejecting SCCs of the pruned config aut, with basin / state-SCC
        fallbacks). See config_graph.compute_good_muller_sets."""
        from . import config_graph as _cg
        return _cg.compute_good_muller_sets(self)

    def _accepting_sc_subsets(self, g, nodes):
        """See config_graph.accepting_sc_subsets (pure function of (g, nodes))."""
        from . import config_graph as _cg
        return _cg.accepting_sc_subsets(g, nodes)

    def get_accepting_scc_indices(self):
        """See config_graph.get_accepting_scc_indices."""
        from . import config_graph as _cg
        return _cg.get_accepting_scc_indices(self)

    def states_in_basin_of_scc(self, scc_index):
        """See config_graph.states_in_basin_of_scc."""
        from . import config_graph as _cg
        return _cg.states_in_basin_of_scc(self, scc_index)

    def configs_in_basin_of_scc(self, scc_index):
        """See config_graph.configs_in_basin_of_scc."""
        from . import config_graph as _cg
        return _cg.configs_in_basin_of_scc(self, scc_index)

    def configs_in_scc(self, scc_index):
        """See config_graph.configs_in_scc."""
        from . import config_graph as _cg
        return _cg.configs_in_scc(self, scc_index)

    def get_good_muller_sets_from_basins(self):
        """See config_graph.get_good_muller_sets_from_basins."""
        from . import config_graph as _cg
        return _cg.get_good_muller_sets_from_basins(self)


def make_trivial_cascade(n_states: int = 1) -> Cascade:
    """Factory for the degenerate 0- or 1-state case (useful for tests)."""
    return Cascade(
        num_levels=1,
        levels=[LevelInfo(index=0, size=n_states, kind="reset")],
        num_states=n_states,
        state_to_config={s: (s+1,) for s in range(n_states)},  # 1-based convention
        config_to_state={(s+1,): s for s in range(n_states)},
    )
