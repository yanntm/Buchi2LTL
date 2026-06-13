"""
acceptance_dispatch.py — direct hierarchy-class φ per Theorem 2 / construction
-ref §9.3, ORTHOGONAL to the Muller-DNF assembly (reachability.py untouched).

The Muller DNF (`reconstruct_ltl_paper_style`) is the general `Δ₂` form and the
explosive one: it enumerates good config-sets G and, per G, asserts the inf-set
is *exactly* G via ⋀_{C∈G}¬Fin(C) ∧ ⋀_{C∉G}Fin(C). For the simpler acceptance
classes Theorem 2 gives a direct φ that avoids both explosions.

**Büchi** (recurrence, `Π₂`). For a deterministic Büchi cascade, acceptance is
"some accepting config is visited infinitely often", so

    φ_Büchi := ⋁_{C ∈ accepting configs} ¬Fin(C)              (§9.3, Π₂)

— no `Fin(C∉G)` web and no good-set enumeration. Soundness: `¬Fin(C)` ≡
"C ∈ inf-set"; the i.o.-set of a run is strongly connected, so Büchi acceptance
`inf ∩ α ≠ ∅` ≡ `⋁_{C∈α} (C ∈ inf)` ≡ `⋁_{C∈α} ¬Fin(C)` (a transient accepting
C contributes `¬Fin(C) ≡ false`, harmless). Returns None when the cascade is
not Büchi so the caller falls back to the Muller path.

**coBüchi** (persistence, `Σ₂`) is the mirror: acceptance is `Inf(ρ) ∩ Marked =
∅` (the rejecting/marked configs are visited only finitely), so

    φ_coBüchi := ⋀_{C ∈ marked configs} Fin(C)               (§9.3, Σ₂)

— exact (no strongly-connected argument needed; a transient marked C contributes
`Fin(C) ≡ true`, harmless). GATE SUBTLETY: `decompose_aut`'s parity normalization
turns the natural `Fin(0)` into `Inf(0) | Fin(1)`, on which `acc().is_co_buchi()`
is False — so the gate recovers the natural acceptance via
`postprocess(.,"generic")` and tests `is_co_buchi` there (the `postprocess(.,
"coBuchi")` variant is UNSOUND — a recurrence cascade like GFa passes it). Büchi
is tried first, so coBüchi only sees genuinely-not-Büchi cascades.

Probe/verify: kr/testing/probe_buchi_dispatch.py and probe_cobuchi_dispatch.py
(equiv vs original, size A/B, gate). looping/weak are TODO.
"""

from __future__ import annotations
from typing import Optional

import kr.reachability_operators as _ops
from kr.fin import fin_c
from kr.ltl_builders import _And, _Or, _Not, _tt, _ff, _simp_f, _tree_size_f
from kr.cascade import Cascade


def is_buchi_cascade(casc: Cascade) -> bool:
    """True iff the cascade's normalized D carries a plain Büchi condition
    (`Inf(0)`), so the direct Büchi dispatch applies."""
    if casc.num_levels == 0 or casc.original_aut is None:
        return False
    try:
        return bool(casc.original_aut.acc().is_buchi())
    except Exception:
        return False


def is_cobuchi_cascade(casc: Cascade) -> bool:
    """True iff the cascade's language is coBüchi-recognizable (persistence), so
    the direct coBüchi dispatch applies. Tested on the NATURAL acceptance recovered
    via `postprocess(.,"generic")` — NOT on the cascade's parity-normalized
    condition (`Inf(0)|Fin(1)`, on which `is_co_buchi()` is False) and NOT via
    `postprocess(.,"coBuchi")` (unsound: recurrence cascades pass it)."""
    if casc.num_levels == 0 or casc.original_aut is None:
        return False
    try:
        import spot
        gen = spot.postprocess(casc.original_aut, "deterministic", "generic")
        return bool(gen.acc().is_co_buchi())
    except Exception:
        return False


def _reset_ops(casc: Cascade) -> None:
    """Fresh-build reset of the operator counters/memos (mirrors
    reconstruct_ltl_paper_style) so a dispatch build is independent and its
    size counters are accurate."""
    _ops.PAPER_REACH_CALLS = 0
    _ops.PAPER_FIN_CALLS = 0
    _ops.PAPER_MAX_LTL_SIZE = 0
    if hasattr(_ops, "_reach_memo"):
        _ops._reach_memo.clear()
    _ops._clear_casc_registry()
    _ops._register_casc(casc)
    if hasattr(_ops, "_lru_reach_strong"):
        _ops._lru_reach_strong.cache_clear()
    if hasattr(_ops, "_helper_memo"):
        _ops._helper_memo.clear()


def reconstruct_buchi(casc: Cascade) -> Optional["spot.formula"]:
    """Direct Büchi φ = ⋁_{C ∈ accepting configs} ¬Fin(C), or None if the
    cascade is not Büchi.

    α comes from `buchi_accepting_configs()` — the COVER-AWARE reader off the
    pruned config aut — NOT the lift-section `accepting_configs()`: on a genuine
    holonomy cover (duplicated accepting sinks) the lift section returns only one
    config per accepting state and the disjunction then UNDER-approximates
    (witness `F(a & X b)`: lift α={(1,2)} gives L⊊L(orig); cover α={(1,1),(1,2)}
    is exact). A transient accepting config only adds a `¬Fin(C)≡false` disjunct,
    so the (possibly looser) cover set stays sound."""
    if not is_buchi_cascade(casc):
        return None
    _reset_ops(casc)
    acc_cfgs = sorted(casc.buchi_accepting_configs())
    if not acc_cfgs:
        return _ff()    # Büchi with no recurrent accepting config -> empty
    res = _simp_f(_Or(*[_Not(fin_c(c, casc)) for c in acc_cfgs]))
    _ops.PAPER_MAX_LTL_SIZE = _tree_size_f(res)
    return res


def reconstruct_cobuchi(casc: Cascade) -> Optional["spot.formula"]:
    """Direct coBüchi φ = ⋀_{C ∈ marked configs} Fin(C), or None if the cascade
    is not coBüchi (persistence). α = `cobuchi_finite_configs()`, the cover-aware
    "visit finitely" set (dual of the Büchi reader). Empty α (nothing must be
    visited finitely) means every run is accepting -> `true`."""
    if not is_cobuchi_cascade(casc):
        return None
    _reset_ops(casc)
    fin_cfgs = sorted(casc.cobuchi_finite_configs())
    if not fin_cfgs:
        return _tt()    # coBüchi with no marked config -> all runs accept
    res = _simp_f(_And(*[fin_c(c, casc) for c in fin_cfgs]))
    _ops.PAPER_MAX_LTL_SIZE = _tree_size_f(res)
    return res


# --- Weak (Δ₁) / looping (Σ₁/Π₁): pure reach_to, NO Fin (§9.3). EXPERIMENTAL,
# OFF by default (KR_DISPATCH_WEAK). The cascade weak form is a size REGRESSION
# vs the Büchi/coBüchi dispatch on most weak cases (probe_weak_dispatch /
# probe_looping_dispatch): weak languages are Büchi AND coBüchi recognizable, so
# those already produce smaller forms, and the residual here is reach-driven (the
# τ-tail), not acceptance-driven. Kept in, flagged off, for A/B against the
# forthcoming config-indexed Acc(c) weak-class construction. ---

def _reach_to(S, C, casc) -> "spot.formula":
    """reach_to(S,C) := reach(S, C, false, C, true) — "reach config C from S",
    no real bad (β=false), no Fin. §9.1 shorthand over reach_strong."""
    return _ops.reach_strong(S, C, _ff(), C, _tt(), casc, 0)


def _init_config(casc: Cascade):
    """The initial configuration ι (lift of D's initial state), reachable-config
    fallback."""
    if casc.original_aut is not None:
        try:
            ic = casc.state_to_config.get(casc.original_aut.get_init_state_number())
            if ic is not None:
                return ic
        except Exception:
            pass
    r = casc.reachable_configs()
    return r[0] if r else None


def is_weak_cascade(casc: Cascade) -> bool:
    """True iff the cascade's language is WEAK-recognizable (obligation/safety/
    guarantee), so the direct Δ₁ weak form applies. Like the coBüchi gate, tested
    on the NATURAL automaton recovered via postprocess->generic (the parity step
    can destroy weakness), NOT on the parity cascade directly."""
    if casc.num_levels == 0 or casc.original_aut is None:
        return False
    try:
        import spot
        gen = spot.postprocess(casc.original_aut, "deterministic", "generic")
        return bool(spot.is_weak_automaton(gen))
    except Exception:
        return False


def reconstruct_weak(casc: Cascade) -> Optional["spot.formula"]:
    """Direct weak (Δ₁) φ := ⋁ over accepting SCC G of the config aut : end_in(G),
    with end_in(G) = (⋁_{C∈H} reach_to(ι,C)) ∧ (⋀_{C'∈G'} ¬reach_to(ι,C')),
    H = configs of G, G' = configs reachable from G but not in G (the run must
    SETTLE in G). Pure reach_to — no Fin. Returns None if the cascade is not weak.

    Subsumes looping-Büchi (safety, single rejecting sink ⇒ end_in over the live
    SCC reduces to ⋀¬reach_to(sink)) and looping-coBüchi (guarantee). See the
    module note above: experimental, OFF by default, a size regression — the
    residual is the reach τ-tail."""
    if not is_weak_cascade(casc):
        return None
    from kr.config_graph import build_pruned_config_aut, reachable_configs
    import spot
    _reset_ops(casc)
    g = build_pruned_config_aut(casc)
    if g is None:
        return None
    reach = reachable_configs(casc)         # node i <-> reach[i]
    iota = _init_config(casc)
    si = spot.scc_info(g)
    terms = []
    for i in range(si.scc_count()):
        if si.is_rejecting_scc(i):
            continue
        nodes = [k for k in range(g.num_states()) if si.scc_of(k) == i]
        nodeset = set(nodes)
        # G' = configs reachable from G in the config aut, not in G
        visited, stack, gprime = set(nodes), list(nodes), set()
        while stack:
            u = stack.pop()
            for e in g.out(u):
                if e.dst not in visited:
                    visited.add(e.dst)
                    if e.dst not in nodeset:
                        gprime.add(e.dst)
                    stack.append(e.dst)
        reach_in = _Or(*[_reach_to(iota, reach[k], casc) for k in nodes])
        avoid_out = (_And(*[_Not(_reach_to(iota, reach[k], casc)) for k in gprime])
                     if gprime else _tt())
        terms.append(_And(reach_in, avoid_out))
    if not terms:
        return _ff()    # no accepting SCC -> empty language
    res = _simp_f(_Or(*terms))
    _ops.PAPER_MAX_LTL_SIZE = _tree_size_f(res)
    return res


__all__ = ["is_buchi_cascade", "reconstruct_buchi",
           "is_cobuchi_cascade", "reconstruct_cobuchi",
           "is_weak_cascade", "reconstruct_weak"]
