"""
Lightweight representation of a holonomy (Krohn-Rhodes) cascade produced by SgpDec.

This is the Python-side bridge object that the rest of the pipeline (and future
LTL synthesis) will consume. It is intentionally simple and serializable.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, NamedTuple, FrozenSet
import buddy  # for bddtrue in config aut edge labels (Spot twa_graph.new_edge cond; spot.bddtrue not exposed)

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

    def accepting_configs(self) -> set:
        """Configs from which accepting infinite runs can recur (w.r.t. our D).

        The stored aut is the normalized deterministic complete parity aut
        (our authoritative input D after Spot transformations). We use
        spot.scc_info on it to identify non-rejecting SCCs that contain at
        least one cycle with an accepting mark (per the parity condition on D).
        Returns the corresponding cascade configs for those states.
        Special-cases trivial "t"/"true"/"f"/"false" acceptance conditions on D.
        Returns empty set if no aut or on analysis error.
        """
        if self.original_aut is None:
            return set()
        aut = self.original_aut
        acc_cond = str(aut.get_acceptance()).strip().lower()
        if acc_cond in ("t", "true", "1") or acc_cond == "0 t":
            return set(self.state_to_config.values())
        if acc_cond in ("f", "false", "0 f"):
            return set()
        try:
            si = spot.scc_info(aut)
            acc_configs = set()
            for scci in range(si.scc_count()):
                if not si.is_rejecting_scc(scci):
                    states_in = [s for s in range(aut.num_states()) if si.scc_of(s) == scci]
                    has_cycle = False
                    for s in states_in:
                        for e in aut.out(s):
                            if e.dst in states_in:
                                has_cycle = True
                                break
                        if has_cycle:
                            break
                    if has_cycle or len(states_in) > 1:
                        for s in states_in:
                            if s in self.state_to_config:
                                has_acc_on_cycle = False
                                for e in aut.out(s):
                                    if e.dst in states_in and e.acc and list(e.acc.sets()):
                                        has_acc_on_cycle = True
                                        break
                                if has_acc_on_cycle:
                                    acc_configs.add(self.state_to_config[s])
            if acc_configs:
                return acc_configs
        except Exception:
            pass
        # Fallback: edge acc marks only on self-loops (internal cycles for singletons).
        # (This is on the normalized D; transients with acc only on exit edges are avoided.)
        acc_configs = set()
        for s, c in self.state_to_config.items():
            try:
                for e in aut.out(s):
                    if e.acc and list(e.acc.sets()) and e.dst == s:  # self-loop with acc
                        acc_configs.add(c)
                        break
            except Exception:
                pass
        # prune to reachable from init (using config aut exploration)
        try:
            reach = set(self.reachable_configs())
            acc_configs = {c for c in acc_configs if c in reach}
        except Exception:
            pass
        return acc_configs


    def summary(self) -> str:
        lv_str = ", ".join(f"L{i}:{lv.size}{('('+lv.structure+')' if lv.structure else '')}"
                           for i, lv in enumerate(self.levels))
        return (f"Cascade(n_states={self.num_states}, levels={self.num_levels} "
                f"[{lv_str}])")

    def __repr__(self) -> str:
        return self.summary()

    # ------------------------------------------------------------------
    # New: proper use of the configuration automaton + pruning (for point 2)
    # We compute reachable configs from init via BFS on move_config.
    # We build a pruned config twa (with acc lifted per transition from D).
    # We compute good Muller sets via scc_info on the *config* graph (pruned, reachable from init).
    # This enumerates recurrent accepting config sets on actual paths from ι (model checking
    # the lifted structure), as recommended in the paper/algo2. No more shying from the
    # config aut; for our sizes it's fine.
    # ------------------------------------------------------------------

    def reachable_configs(self) -> list:
        """BFS from the initial config (using move_config over letters).
        Returns sorted list of reachable config tuples. Prunes irrelevant configs.
        """
        if not self.state_to_config:
            return []
        init_c = None
        if self.original_aut is not None:
            try:
                init_s = self.original_aut.get_init_state_number()
                init_c = self.state_to_config.get(init_s)
            except Exception:
                pass
        if init_c is None:
            init_c = next(iter(self.state_to_config.values()))
        from collections import deque
        visited = set()
        q = deque([init_c])
        visited.add(init_c)
        while q:
            c = q.popleft()
            for li in range(self.num_letters()):
                try:
                    nc = self.move_config(c, li)
                    if nc not in visited:
                        visited.add(nc)
                        q.append(nc)
                except Exception:
                    continue
        return sorted(list(visited))

    def build_pruned_config_aut(self):
        """Return a Spot twa_graph on reachable configs only, with transitions and
        acc marks lifted from the corresponding transitions in the normalized D
        (self.original_aut). This is the pruned cascade graph for proper SCC/Muller
        analysis on the config side.
        """
        reach = self.reachable_configs()
        if not reach or self.original_aut is None:
            return None
        import spot
        orig = self.original_aut
        idx = {c: i for i, c in enumerate(reach)}
        n = len(reach)
        g = spot.make_twa_graph()
        # Copy acceptance condition properly (Spot API: use acc() for cond, then num + code)
        acc = orig.acc()
        g.set_acceptance( acc.num_sets() , acc.get_acceptance() )
        g.new_states(n)
        # init config
        init_c = None
        if self.original_aut is not None:
            try:
                is_ = self.original_aut.get_init_state_number()
                ic = self.state_to_config.get(is_)
                if ic in idx:
                    init_c = ic
            except Exception:
                pass
        if init_c is None:
            init_c = reach[0]
        g.set_init_state(idx[init_c])
        for i, c in enumerate(reach):
            s = self.state_of(c)
            if s is None:
                continue
            for li in range(self.num_letters()):
                try:
                    nc = self.move_config(c, li)
                    if nc not in idx:
                        continue
                    j = idx[nc]
                    ts = self.state_of(nc)
                    for e in orig.out(s):
                        if e.dst == ts:
                            g.new_edge(i, j, buddy.bddtrue, e.acc)
                            break
                except Exception:
                    continue
        return g

    def compute_good_muller_sets(self):
        """Good M on configs using SCC analysis on the pruned *config* automaton
        (reachable from init, acc lifted). This is the correct way to extract
        the possible i.o. config sets for accepting runs (pruned graph + scc
        on configs, per paper/algo2).

        We also support basin-based good Ms (using Spot's decompose-scc=aN style):
        for each accepting SCC in the normalized D, compute the attraction basin
        (states that can reach it, i.e. the "sub-automaton leading to" it), map
        to configs. This gives precise per-accepting-component recurrent sets
        via explicit BFS exploration (backward reachability).

        Prefers config-graph SCCs (on pruned config aut). Falls back to basins
        or pruned state-SCCs.
        """
        # 1. Direct config-graph analysis (best, on the lifted pruned structure):
        #    the Muller alpha' contains every realizable inf-set, i.e. every
        #    reachable subset M inducing a strongly connected subgraph that is
        #    accepting -- not just whole SCCs (e.g. GFa needs the accepting
        #    self-loop subset of its single SCC; conversely a whole SCC whose
        #    mark union is rejecting must NOT be emitted). Rejecting SCCs
        #    contain no accepting cycle, hence no accepting subset: skipped.
        g = self.build_pruned_config_aut()
        if g is not None:
            try:
                import spot
                si = spot.scc_info(g)
                reach = self.reachable_configs()
                good = []
                for scci in range(si.scc_count()):
                    if si.is_rejecting_scc(scci):
                        continue
                    nodes = [k for k in range(g.num_states()) if si.scc_of(k) == scci]
                    for combo in self._accepting_sc_subsets(g, nodes):
                        m = frozenset(reach[k] for k in combo)
                        if m:
                            good.append(m)
                if good:
                    return good
            except Exception:
                pass

        # 2. Try basin-based (decompose-scc / aN idea on the state D, lifted to configs)
        try:
            basin_good = self.get_good_muller_sets_from_basins()
            if basin_good:
                return basin_good
        except Exception:
            pass

        # 3. Fallback: pruned state-SCC mapping (old logic, now with reach prune)
        reach = set(self.reachable_configs())
        if self.original_aut is None:
            acc = self.accepting_configs()
            acc = {c for c in acc if c in reach}
            return [frozenset([c]) for c in acc] if acc else []
        aut = self.original_aut
        try:
            import spot
            si = spot.scc_info(aut)
        except Exception:
            acc = self.accepting_configs()
            acc = {c for c in acc if c in reach}
            return [frozenset([c]) for c in acc] if acc else []
        good = []
        for scci in range(si.scc_count()):
            if not si.is_rejecting_scc(scci):
                states = [s for s in range(aut.num_states()) if si.scc_of(s) == scci]
                m = frozenset(self.state_to_config.get(s) for s in states
                              if s in self.state_to_config and self.state_to_config.get(s) in reach)
                if m:
                    good.append(m)
        return good

    def _accepting_sc_subsets(self, g, nodes):
        """Yield the subsets of `nodes` (the states of one non-rejecting SCC
        of the pruned config aut g) that induce a strongly connected subgraph
        (singletons need a self-loop) and are accepting per g's acceptance.

        A run whose inf-set of configs is exactly M visits infinitely often
        exactly the marks on the in-M edges; under state-based acceptance
        (guaranteed by the sbacc normalization in decompose_aut) all out-edges
        of a state carry the same marks, so the union over induced edges is
        run-independent and `g.acc().accepting(union)` is an exact oracle.

        Enumeration is exponential in the SCC size, gated by
        KR_MULLER_SCC_LIMIT (default 12); beyond the limit we emit only the
        whole-SCC set and warn (no silent truncation).
        """
        import os
        import sys
        import itertools
        import spot

        nodeset = set(nodes)
        succ = {k: set() for k in nodes}
        emarks = {}
        for k in nodes:
            for e in g.out(k):
                if e.dst in nodeset:
                    succ[k].add(e.dst)
                    key = (k, e.dst)
                    emarks[key] = (emarks[key] | e.acc) if key in emarks else e.acc

        limit = int(os.environ.get("KR_MULLER_SCC_LIMIT", 12))
        if len(nodes) > limit:
            print(
                f"[KR][WARN] Muller subset enumeration truncated: SCC size "
                f"{len(nodes)} > KR_MULLER_SCC_LIMIT={limit}; emitting the "
                f"whole-SCC set only (raise the env var for exactness).",
                file=sys.stderr,
            )
            yield tuple(nodes)
            return

        def strongly_connected(cset):
            start = next(iter(cset))
            if len(cset) == 1:
                return start in succ[start]
            seen = {start}
            stack = [start]
            while stack:
                for v in succ[stack.pop()]:
                    if v in cset and v not in seen:
                        seen.add(v)
                        stack.append(v)
            if seen != cset:
                return False
            rseen = {start}
            stack = [start]
            while stack:
                u = stack.pop()
                for w in cset:
                    if w not in rseen and u in succ[w]:
                        rseen.add(w)
                        stack.append(w)
            return rseen == cset

        acc = g.acc()
        for r in range(1, len(nodes) + 1):
            for combo in itertools.combinations(nodes, r):
                cset = set(combo)
                if not strongly_connected(cset):
                    continue
                mk = spot.mark_t()
                for (u, v), m in emarks.items():
                    if u in cset and v in cset:
                        mk |= m
                if acc.accepting(mk):
                    yield combo

    # ------------------------------------------------------------------
    # Basin / "leading to accepting SCC" helpers, inspired by Spot's
    # --decompose-scc=N / aN  (autfilt).
    #
    # These extract, for each accepting SCC (by index), the attraction basin:
    # all states from which you can reach that SCC (prefix + the SCC itself).
    # Then map to configs.
    #
    # This gives us per-accepting-component config sets that can flow into
    # a specific recurrent accepting set. Perfect for good Ms in the Muller
    # DNF (or for per-basin handling), and directly mirrors the "sub-automaton
    # leading to the Nth accepting SCC" concept.
    #
    # Complements the pruned config aut + its SCCs: we can now also compute
    # basins at the state level (or do analogous on config graph) and use
    # the resulting config sets as precise good Ms.
    # Uses scc_info + our BFS-style exploration (no fear of explosion for
    # our sizes; user confirmed resources allow).
    # ------------------------------------------------------------------

    def get_accepting_scc_indices(self):
        """Return list of 0-based indices of SCCs in the normalized D (original_aut)
        that are non-rejecting and contain at least one accepting cycle/edge.
        (Analogous to counting 'aN' accepting SCCs for decompose.)
        """
        if self.original_aut is None:
            return []
        import spot
        aut = self.original_aut
        try:
            si = spot.scc_info(aut)
            acc_sccs = []
            for i in range(si.scc_count()):
                if si.is_rejecting_scc(i):
                    continue
                states_in = [s for s in range(aut.num_states()) if si.scc_of(s) == i]
                has_acc = False
                for s in states_in:
                    for e in aut.out(s):
                        if e.dst in states_in and e.acc and list(e.acc.sets()):
                            has_acc = True
                            break
                    if has_acc:
                        break
                if has_acc or len(states_in) > 1:
                    acc_sccs.append(i)
            return acc_sccs
        except Exception:
            return []

    def states_in_basin_of_scc(self, scc_index):
        """Return the set of states that can reach the given SCC (the 'leading to'
        basin / attraction set, including the SCC itself).
        This is the set of states in the sub-automaton that autfilt --decompose-scc=aN
        or --decompose-scc=N would extract for that SCC.
        Implemented with backward BFS from the SCC states (using predecessor lists).
        """
        if self.original_aut is None:
            return set()
        import spot
        aut = self.original_aut
        try:
            si = spot.scc_info(aut)
            target_states = {s for s in range(aut.num_states()) if si.scc_of(s) == scc_index}
            if not target_states:
                return set()
            # build predecessors
            preds = {s: [] for s in range(aut.num_states())}
            for s in range(aut.num_states()):
                for e in aut.out(s):
                    preds[e.dst].append(s)
            # backward BFS from targets
            from collections import deque
            visited = set(target_states)
            q = deque(target_states)
            while q:
                s = q.popleft()
                for p in preds.get(s, []):
                    if p not in visited:
                        visited.add(p)
                        q.append(p)
            return visited
        except Exception:
            return set()

    def configs_in_basin_of_scc(self, scc_index):
        """Map the basin states (states leading to + in the SCC) to their configs.
        The full basin includes prefixes that flow into the SCC.
        Returns a frozenset of config tuples. Useful for prefix analysis.
        """
        states = self.states_in_basin_of_scc(scc_index)
        confs = []
        for s in states:
            c = self.state_to_config.get(s)
            if c is not None:
                confs.append(c)
        return frozenset(confs)

    def configs_in_scc(self, scc_index):
        """Return only the configs whose states are exactly inside the given SCC
        (the recurrent / terminal component itself, not the leading prefixes).
        This is the precise set for a good M in the Muller DNF (the configs
        that can be visited i.o. when the run enters this accepting SCC).
        """
        if self.original_aut is None:
            return frozenset()
        import spot
        aut = self.original_aut
        try:
            si = spot.scc_info(aut)
            states = {s for s in range(aut.num_states()) if si.scc_of(s) == scc_index}
            confs = [self.state_to_config.get(s) for s in states if s in self.state_to_config]
            return frozenset(c for c in confs if c is not None)
        except Exception:
            return frozenset()

    def get_good_muller_sets_from_basins(self):
        """Return good Ms derived from accepting SCCs (using the decompose-scc=aN
        / basin idea, but taking the precise recurrent part: the SCC configs themselves).
        For each accepting SCC index, the configs strictly inside that SCC
        (via configs_in_scc) form a good M -- the set that can be visited i.o.
        when a run enters this particular accepting component.
        The full basin (configs_in_basin_of_scc) is available separately for
        prefix/leading-to analysis.
        Uses scc_info + our reachability exploration. Complements the pruned
        config-graph SCC computation.
        """
        acc_indices = self.get_accepting_scc_indices()
        if not acc_indices:
            # fallback to pruned config SCCs if available
            if hasattr(self, 'compute_good_muller_sets'):
                try:
                    return self.compute_good_muller_sets()
                except:
                    pass
            return []
        good = []
        for idx in acc_indices:
            m = self.configs_in_scc(idx)
            if m:
                good.append(m)
        return good


def make_trivial_cascade(n_states: int = 1) -> Cascade:
    """Factory for the degenerate 0- or 1-state case (useful for tests)."""
    return Cascade(
        num_levels=1,
        levels=[LevelInfo(index=0, size=n_states, kind="reset")],
        num_states=n_states,
        state_to_config={s: (s+1,) for s in range(n_states)},  # 1-based convention
        config_to_state={(s+1,): s for s in range(n_states)},
    )
