"""
kr/weak.py — the weak (Δ₁) CascadeTranslator member.

φ := ⋁ over accepting SCC G of the config aut : end_in(G), with
end_in(G) = (⋁_{C∈H} reach_to(ι,C)) ∧ (⋀_{C'∈G'} ¬reach_to(ι,C')), H = configs of
G, G' = configs reachable from G but not in G (the run must SETTLE in G). Pure
reach_to — no Fin. Subsumes looping-Büchi (safety) and looping-coBüchi
(guarantee). Self-gating: declines when the cascade is not weak.

Off by default in the chain (KR_DISPATCH_WEAK): weak languages are also
Büchi/coBüchi recognizable and those produce smaller forms, so this stays a
reach-driven A/B alternative rather than the default.
"""

from __future__ import annotations

import aut2ltl.kr.reachability_operators as _ops
from aut2ltl.kr.ltl_builders import _And, _Or, _Not, _tt, _ff, _simp_f
from aut2ltl.kr.cascade import Cascade, CascadeHolder
from aut2ltl.contract import LTLFormulaResult, CascadeTranslator


def is_weak_cascade(casc: Cascade) -> bool:
    """True iff the cascade's language is weak-recognizable (obligation/safety/
    guarantee), tested on the natural automaton recovered via
    `postprocess(.,"generic")` (the parity step can destroy weakness)."""
    if casc.num_levels == 0 or casc.original_aut is None:
        return False
    try:
        import spot
        gen = spot.postprocess(casc.original_aut, "deterministic", "generic")
        return bool(spot.is_weak_automaton(gen))
    except Exception:
        return False


def _reach_to(S, C, casc) -> "spot.formula":
    """reach_to(S,C) := reach(S, C, false, C, true) — reach config C from S, no
    real bad (β=false), no Fin. §9.1 shorthand over reach_strong."""
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


class Weak:
    """Weak (Δ₁) member: ⋁ over accepting SCC G : end_in(G). Pure reach, no Fin."""

    name = "weak"

    def __call__(self, casc: CascadeHolder) -> LTLFormulaResult:
        if not is_weak_cascade(casc):
            return LTLFormulaResult.decline()
        from aut2ltl.kr.cascade import build_pruned_config_aut, reachable_configs
        import spot
        g = build_pruned_config_aut(casc)
        if g is None:
            return LTLFormulaResult.decline()
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
        res = _ff() if not terms else _simp_f(_Or(*terms))   # no accepting SCC -> empty
        return LTLFormulaResult(formula=res, technique={self.name})


weak: CascadeTranslator = Weak()


__all__ = ["is_weak_cascade", "Weak", "weak"]
