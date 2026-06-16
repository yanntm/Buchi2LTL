"""
config_graph.py — Configuration-graph analysis for a Cascade.

Free functions over a Cascade: reachable configs (BFS), the pruned config
automaton (acceptance lifted from the normalized D), accepting configs,
good Muller sets (incl. the strongly-connected accepting *subset* enumeration),
and the basin helpers (Spot --decompose-scc=aN style).

Split out of cascade.py (cleanup iteration); the Cascade class keeps thin
delegating methods so call sites are unchanged. Bodies moved verbatim
(self → casc), except get_good_muller_sets_from_basins whose fallback used to
recurse back into compute_good_muller_sets (latent infinite recursion only
broken by the caller's exception guard) — it now returns [] and the caller's
own fallback chain proceeds.
"""

from __future__ import annotations
from typing import Optional, Tuple

import buddy  # for bddtrue in config aut edge labels (spot.bddtrue not exposed)


def accepting_configs(casc) -> set:
    """Configs from which accepting infinite runs can recur (w.r.t. our D).

    The stored aut is the normalized deterministic complete parity aut
    (our authoritative input D after Spot transformations). We use
    spot.scc_info on it to identify non-rejecting SCCs that contain at
    least one cycle with an accepting mark (per the parity condition on D).
    Returns the corresponding cascade configs for those states.
    Special-cases trivial "t"/"true"/"f"/"false" acceptance conditions on D.
    Returns empty set if no aut or on analysis error.
    """
    if casc.original_aut is None:
        return set()
    aut = casc.original_aut
    acc_cond = str(aut.get_acceptance()).strip().lower()
    if acc_cond in ("t", "true", "1") or acc_cond == "0 t":
        return set(casc.state_to_config.values())
    if acc_cond in ("f", "false", "0 f"):
        return set()
    try:
        import spot
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
                        if s in casc.state_to_config:
                            has_acc_on_cycle = False
                            for e in aut.out(s):
                                if e.dst in states_in and e.acc and list(e.acc.sets()):
                                    has_acc_on_cycle = True
                                    break
                            if has_acc_on_cycle:
                                acc_configs.add(casc.state_to_config[s])
        if acc_configs:
            return acc_configs
    except Exception:
        pass
    # Fallback: edge acc marks only on self-loops (internal cycles for singletons).
    # (This is on the normalized D; transients with acc only on exit edges are avoided.)
    acc_configs = set()
    for s, c in casc.state_to_config.items():
        try:
            for e in aut.out(s):
                if e.acc and list(e.acc.sets()) and e.dst == s:  # self-loop with acc
                    acc_configs.add(c)
                    break
        except Exception:
            pass
    # prune to reachable from init (using config aut exploration)
    try:
        reach = set(reachable_configs(casc))
        acc_configs = {c for c in acc_configs if c in reach}
    except Exception:
        pass
    return acc_configs


def buchi_accepting_configs(casc) -> set:
    """Accepting configs for the direct Büchi dispatch, COVER-AWARE.

    Unlike `accepting_configs` — which maps accepting *states* to configs through
    `state_to_config` (the lift *section*, one config per state) and so misses the
    other configs that cover the same accepting state on a genuine holonomy cover
    (duplicated sinks etc.) — this reads acceptance directly off the pruned config
    automaton, which enumerates EVERY reachable config and lifts D's marks per
    config-edge (`build_pruned_config_aut`). A config node is accepting iff the
    mark-union on its (state-based, sbacc) out-edges satisfies `g.acc()` — the
    same exact oracle `accepting_sc_subsets` uses.

    This is the α for `φ_Büchi = ⋁_{C∈α}¬Fin(C)`: under a plain Büchi condition a
    single state-accepting config visited i.o. already witnesses acceptance, so α
    must be ALL such configs (a transient one only adds a `¬Fin(C)≡false` disjunct,
    harmless). Falls back to the lift-section `accepting_configs` if the pruned
    config aut is unavailable (degenerate / no original_aut)."""
    g = build_pruned_config_aut(casc)
    if g is None:
        return accepting_configs(casc)
    import spot
    reach = reachable_configs(casc)   # node i <-> reach[i] (builder's ordering)
    acc = g.acc()
    out = set()
    for i in range(g.num_states()):
        mk = spot.mark_t()
        for e in g.out(i):
            mk |= e.acc
        if acc.accepting(mk):
            out.add(reach[i])
    return out


def cobuchi_finite_configs(casc) -> set:
    """The "must be visited finitely" configs for the direct coBüchi dispatch —
    the DUAL of buchi_accepting_configs, read off the same cover-aware pruned
    config aut. A config is in α iff the mark-union on its (sbacc) out-edges makes
    `g.acc()` REJECT (where buchi_accepting_configs keeps the ones that make it
    ACCEPT). This is the α for `φ_coBüchi = ⋀_{C∈α} Fin(C)`: coBüchi acceptance is
    `Inf(ρ) ∩ Marked = ∅`, so the run accepts iff every marked config is visited
    finitely — `⋀ Fin(C)`. A transient marked config only adds a `Fin(C)≡true`
    conjunct (harmless). Cover-aware for the same reason as the Büchi reader (the
    lift section would miss configs covering a marked state on a genuine cover).
    Falls back to the empty set if the pruned config aut is unavailable."""
    g = build_pruned_config_aut(casc)
    if g is None:
        return set()
    import spot
    reach = reachable_configs(casc)
    acc = g.acc()
    out = set()
    for i in range(g.num_states()):
        mk = spot.mark_t()
        for e in g.out(i):
            mk |= e.acc
        if not acc.accepting(mk):
            out.add(reach[i])
    return out


def reachable_configs(casc) -> list:
    """BFS from the initial config (using move_config over letters).
    Returns sorted list of reachable config tuples. Prunes irrelevant configs.
    """
    if not casc.state_to_config:
        return []
    init_c = None
    if casc.original_aut is not None:
        try:
            init_s = casc.original_aut.get_init_state_number()
            init_c = casc.state_to_config.get(init_s)
        except Exception:
            pass
    if init_c is None:
        init_c = next(iter(casc.state_to_config.values()))
    from collections import deque
    visited = set()
    q = deque([init_c])
    visited.add(init_c)
    while q:
        c = q.popleft()
        for li in range(casc.num_letters()):
            try:
                nc = casc.move_config(c, li)
                if nc not in visited:
                    visited.add(nc)
                    q.append(nc)
            except Exception:
                continue
    return sorted(list(visited))


def configs_reachable_from(casc, sources) -> set:
    """Forward-reachable config set from `sources` in the config graph
    (`move_config` over all letters, BFS). Includes the sources themselves.

    Used by the Muller-DNF assembly for the per-conjunct Fin fold: for a good
    set M, keep Fin(C) only for C ∈ reachable-from-M; drop it for every other
    C ∉ M. Soundness (per Muller term): a run satisfying ⋀_{C'∈M}¬Fin(C') has
    Inf(ρ) ⊇ M, and Inf(ρ) is strongly connected in the config graph (the
    i.o.-set of a path in a finite digraph is strongly connected), so any
    C ∈ Inf(ρ) is reachable from M within Inf(ρ). Contrapositive: C unreachable
    from M ⟹ C ∉ Inf(ρ) ⟹ Fin(C) — so Fin(C) is implied by ⋀_{C'∈M}¬Fin(C')
    and is droppable. A pure graph property (no language/containment check), so
    it scales. Generalizes the absorbing-M fold: M absorbing ⟺
    reachable-from-M == M, which drops every Fin(C∉M); a non-absorbing M still
    drops the Fin(C) off its reachable cone.

    On any move_config failure the result is over-approximated to all configs
    (so the caller keeps every Fin conjunct) — never unsound, only larger.
    """
    from collections import deque
    visited = set(sources)
    if not visited:
        return visited
    nletters = casc.num_letters()
    q = deque(visited)
    while q:
        c = q.popleft()
        for li in range(nletters):
            try:
                nc = casc.move_config(c, li)
            except Exception:
                return set(casc.all_configs()) | visited
            if nc not in visited:
                visited.add(nc)
                q.append(nc)
    return visited


def build_pruned_config_aut(casc):
    """Return a Spot twa_graph on reachable configs only, with transitions and
    acc marks lifted from the corresponding transitions in the normalized D
    (casc.original_aut). This is the pruned cascade graph for proper SCC/Muller
    analysis on the config side.
    """
    reach = reachable_configs(casc)
    if not reach or casc.original_aut is None:
        return None
    import spot
    orig = casc.original_aut
    idx = {c: i for i, c in enumerate(reach)}
    n = len(reach)
    g = spot.make_twa_graph()
    # Copy acceptance condition properly (Spot API: use acc() for cond, then num + code)
    acc = orig.acc()
    g.set_acceptance( acc.num_sets() , acc.get_acceptance() )
    g.new_states(n)
    # init config
    init_c = None
    if casc.original_aut is not None:
        try:
            is_ = casc.original_aut.get_init_state_number()
            ic = casc.state_to_config.get(is_)
            if ic in idx:
                init_c = ic
        except Exception:
            pass
    if init_c is None:
        init_c = reach[0]
    g.set_init_state(idx[init_c])
    for i, c in enumerate(reach):
        s = casc.state_of(c)
        if s is None:
            continue
        for li in range(casc.num_letters()):
            try:
                nc = casc.move_config(c, li)
                if nc not in idx:
                    continue
                j = idx[nc]
                ts = casc.state_of(nc)
                for e in orig.out(s):
                    if e.dst == ts:
                        g.new_edge(i, j, buddy.bddtrue, e.acc)
                        break
            except Exception:
                continue
    return g


def compute_good_muller_sets(casc):
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
    g = build_pruned_config_aut(casc)
    if g is not None:
        try:
            import spot
            si = spot.scc_info(g)
            reach = reachable_configs(casc)
            good = []
            for scci in range(si.scc_count()):
                if si.is_rejecting_scc(scci):
                    continue
                nodes = [k for k in range(g.num_states()) if si.scc_of(k) == scci]
                for combo in accepting_sc_subsets(g, nodes):
                    m = frozenset(reach[k] for k in combo)
                    if m:
                        good.append(m)
            if good:
                return good
        except Exception:
            pass

    # 2. Try basin-based (decompose-scc / aN idea on the state D, lifted to configs)
    try:
        basin_good = get_good_muller_sets_from_basins(casc)
        if basin_good:
            return basin_good
    except Exception:
        pass

    # 3. Fallback: pruned state-SCC mapping (old logic, now with reach prune)
    reach = set(reachable_configs(casc))
    if casc.original_aut is None:
        acc = accepting_configs(casc)
        acc = {c for c in acc if c in reach}
        return [frozenset([c]) for c in acc] if acc else []
    aut = casc.original_aut
    try:
        import spot
        si = spot.scc_info(aut)
    except Exception:
        acc = accepting_configs(casc)
        acc = {c for c in acc if c in reach}
        return [frozenset([c]) for c in acc] if acc else []
    good = []
    for scci in range(si.scc_count()):
        if not si.is_rejecting_scc(scci):
            states = [s for s in range(aut.num_states()) if si.scc_of(s) == scci]
            m = frozenset(casc.state_to_config.get(s) for s in states
                          if s in casc.state_to_config and casc.state_to_config.get(s) in reach)
            if m:
                good.append(m)
    return good


def accepting_sc_subsets(g, nodes):
    """Yield the subsets of `nodes` (the states of one non-rejecting SCC
    of the pruned config aut g) that induce a strongly connected subgraph
    (singletons need a self-loop) and are accepting per g's acceptance.

    A run whose inf-set of configs is exactly M visits infinitely often
    exactly the marks on the in-M edges; under state-based acceptance
    (guaranteed by the sbacc normalization in decompose_aut) all out-edges
    of a state carry the same marks, so the union over induced edges is
    run-independent and `g.acc().accepting(union)` is an exact oracle.

    Enumeration is exponential in the SCC size and EXACT: every accepting
    strongly-connected subset is yielded, with NO cap. Soundness requires the
    full family — emitting a coarser set (e.g. the whole SCC only) would build a
    non-equivalent formula. If the enumeration explodes the run simply times out;
    we never approximate.
    """
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


# ---------------------------------------------------------------------------
# Basin / "leading to accepting SCC" helpers, inspired by Spot's
# --decompose-scc=N / aN (autfilt). For each accepting SCC (by index), the
# attraction basin = all states that can reach it (prefix + the SCC itself),
# mapped to configs. Complements the pruned-config-aut SCC computation.
# ---------------------------------------------------------------------------

def get_accepting_scc_indices(casc):
    """Return list of 0-based indices of SCCs in the normalized D (original_aut)
    that are non-rejecting and contain at least one accepting cycle/edge.
    (Analogous to counting 'aN' accepting SCCs for decompose.)
    """
    if casc.original_aut is None:
        return []
    import spot
    aut = casc.original_aut
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


def states_in_basin_of_scc(casc, scc_index):
    """Return the set of states that can reach the given SCC (the 'leading to'
    basin / attraction set, including the SCC itself).
    This is the set of states in the sub-automaton that autfilt --decompose-scc=aN
    or --decompose-scc=N would extract for that SCC.
    Implemented with backward BFS from the SCC states (using predecessor lists).
    """
    if casc.original_aut is None:
        return set()
    import spot
    aut = casc.original_aut
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


def configs_in_basin_of_scc(casc, scc_index):
    """Map the basin states (states leading to + in the SCC) to their configs.
    The full basin includes prefixes that flow into the SCC.
    Returns a frozenset of config tuples. Useful for prefix analysis.
    """
    states = states_in_basin_of_scc(casc, scc_index)
    confs = []
    for s in states:
        c = casc.state_to_config.get(s)
        if c is not None:
            confs.append(c)
    return frozenset(confs)


def configs_in_scc(casc, scc_index):
    """Return only the configs whose states are exactly inside the given SCC
    (the recurrent / terminal component itself, not the leading prefixes).
    This is the precise set for a good M in the Muller DNF (the configs
    that can be visited i.o. when the run enters this accepting SCC).
    """
    if casc.original_aut is None:
        return frozenset()
    import spot
    aut = casc.original_aut
    try:
        si = spot.scc_info(aut)
        states = {s for s in range(aut.num_states()) if si.scc_of(s) == scc_index}
        confs = [casc.state_to_config.get(s) for s in states if s in casc.state_to_config]
        return frozenset(c for c in confs if c is not None)
    except Exception:
        return frozenset()


def get_good_muller_sets_from_basins(casc):
    """Return good Ms derived from accepting SCCs (using the decompose-scc=aN
    / basin idea, but taking the precise recurrent part: the SCC configs themselves).
    For each accepting SCC index, the configs strictly inside that SCC
    (via configs_in_scc) form a good M -- the set that can be visited i.o.
    when a run enters this particular accepting component.
    The full basin (configs_in_basin_of_scc) is available separately for
    prefix/leading-to analysis.
    """
    acc_indices = get_accepting_scc_indices(casc)
    if not acc_indices:
        return []
    good = []
    for idx in acc_indices:
        m = configs_in_scc(casc, idx)
        if m:
            good.append(m)
    return good


def good_muller_sets(casc) -> list:
    """The good Müller sets M on configs (w.r.t. the normalized D) — the entry
    the BLS assembly consumes.

    Prefers the config-graph computation (`casc.compute_good_muller_sets`):
    reachable configs from init, the pruned config twa with lifted acceptance,
    scc_info on the config graph, non-rejecting SCCs giving the recurrent config
    sets that can occur i.o. on accepting paths. Falls back to state-SCC mapping
    on D (pruned to reachable) if that analysis is unavailable.
    """
    import spot
    # Prefer the config-graph based computation (pruned + actual use of config aut)
    if hasattr(casc, 'compute_good_muller_sets'):
        try:
            res = casc.compute_good_muller_sets()
            if res is not None:
                return res
        except Exception:
            pass
    # Fallback: state-SCC mapping on D, pruned to reachable configs.
    reach = set(casc.reachable_configs()) if hasattr(casc, 'reachable_configs') else set(casc.all_configs())
    if casc.original_aut is None:
        acc = casc.accepting_configs()
        acc = {c for c in acc if c in reach}
        return [frozenset([c]) for c in acc] if acc else []
    aut = casc.original_aut  # the normalized det D (our working automaton)
    try:
        si = spot.scc_info(aut)
    except Exception:
        acc = casc.accepting_configs()
        acc = {c for c in acc if c in reach}
        return [frozenset([c]) for c in acc] if acc else []
    good = []
    for scci in range(si.scc_count()):
        if not si.is_rejecting_scc(scci):
            states = [s for s in range(aut.num_states()) if si.scc_of(s) == scci]
            m = frozenset(casc.state_to_config.get(s) for s in states if s in casc.state_to_config and casc.state_to_config.get(s) in reach)
            if m:
                good.append(m)
    return good
