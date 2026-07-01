"""The `DaisystarDet` combinator Translator — the DETERMINISTIC anchored read-off.

Where `Daisystar` emits the flat `LEAVE` (gate-rescued, not exact), `DaisystarDet`
applies when the initial **rejecting** SCC has a **deterministic L-partition**
(phase = last letter, partscc's precondition) and emits a flat, fixpoint-free,
**exact** candidate — partscc's transition law, but `U`-to-an-exit instead of
`G`-with-fairness (the reachability dual). It is partscc for an *exiting* SCC:

    cand = O(h) ∧ ( exit_at_0 ∨ ( ⋀_p (L(p) → X O(p)) U exit_after_entry ) )
    exit_after_entry = ⋁_{p, exit p→dst} ( L(p) ∧ X(γ ∧ X φ_dst) )
    exit_at_0        = ⋁_{exit h→dst}    ( γ ∧ X φ_dst )

with `L(p)=⋁` guards entering `p` in `C`, `O(p)=⋁` all out-guards of `p`, and
`φ_dst` the child label of an exit target. The `O(h)` anchor + per-revisit law is
exactly what the flat `LEAVE` lacked — for a deterministic L-partition the run is
unique, so the pointwise law equals run legality and the construction is exact (no
phase looseness). It is *not* restricted to length-1 stars: any rejecting SCC with
a deterministic L-partition and at least one exit qualifies.

It still adopts under a Spot equivalence gate (so an unproven case or a
non-deterministic-exit surprise simply declines), with `DAISYSTARDET_TRACE`
printing every gate REJECT and its witnesses — including a *local* (suffix-blind)
re-check, see `_validates`.
"""

import os
import sys
from typing import Dict, List, Tuple, TYPE_CHECKING

import spot

from aut2ltl.language import Language
from aut2ltl.result import LTLResult, Status
from aut2ltl.printer import format_language, format_result
from .shape import init_scc_states, scc_data, is_deterministic, exit_word, reroot

if TYPE_CHECKING:
    from aut2ltl.translator import Translator

_NAME = "daisystardet"
_F = spot.formula
# DAISYSTARDET_TRACE, or the global TRANSLATOR_TRACE_ON which lights every
# translator trace at once. Every use guards with `if _TRACE:` BEFORE building its
# message, so a formula is never flattened for a trace that will not be printed.
_TRACE = "DAISYSTARDET_TRACE" in os.environ or "TRANSLATOR_TRACE_ON" in os.environ


def _out(res: "LTLResult") -> "LTLResult":
    """Trace the outgoing result (status / size / formula), pass it through unchanged."""
    if _TRACE:
        print("[daisystardet] out " + format_result(res), file=sys.stderr)
    return res


def _or(fs: List["spot.formula"]) -> "spot.formula":
    return _F.Or(fs) if fs else _F.ff()


def _and(fs: List["spot.formula"]) -> "spot.formula":
    return _F.And(fs) if fs else _F.tt()


def build_det_candidate(
    aut: "spot.twa_graph", C: "set", h: int,
    L: Dict[int, "buddy.bdd"], O: Dict[int, "buddy.bdd"],
    exits: Dict[int, List[Tuple["buddy.bdd", int]]],
    phi: Dict[int, "spot.formula"],
) -> "spot.formula":
    """The deterministic anchored read-off (see module docstring). Free function so
    a probe can inspect the exact formula gated. `phi` maps each exit target to its
    child label."""
    d = aut.get_dict()

    def f(bdd: "buddy.bdd") -> "spot.formula":
        return spot.bdd_to_formula(bdd, d)

    states = sorted(C)
    law = _and([_F.Or([_F.Not(f(L[p])), _F.X(f(O[p]))]) for p in states])
    after = [
        _F.And([f(L[p]), _F.X(_F.And([f(g), _F.X(phi[dst])]))])
        for p in states for g, dst in exits[p]
    ]
    exit_at_0 = _or([_F.And([f(g), _F.X(phi[dst])]) for g, dst in exits[h]])
    return _F.And([f(O[h]), _F.Or([exit_at_0, _F.U(law, _or(after))])])


def _validates(aut: "spot.twa_graph", phi: "spot.formula") -> bool:
    """Soundness gate: adopt `φ` only if language-equivalent to the input. On a
    REJECT under `DAISYSTARDET_TRACE`, print the candidate and a containment
    witness each way, so a real peeling bug is visible (and distinguishable from a
    suffix the oracle cannot handle)."""
    try:
        cand = phi.translate("GeneralizedBuchi", "Small", "High")
        if spot.are_equivalent(aut, cand):
            return True
        if _TRACE:
            try:
                loose = cand.intersecting_word(spot.complement(aut))
                tight = aut.intersecting_word(spot.complement(cand))
            except Exception as e:
                loose = tight = f"<witness error: {e}>"
            print(f"[daisystardet] gate REJECT: cand={phi}", file=sys.stderr)
            print(f"[daisystardet]     too loose (cand\\input): {loose}", file=sys.stderr)
            print(f"[daisystardet]     too tight (input\\cand): {tight}", file=sys.stderr)
        return False
    except Exception as e:
        if _TRACE:
            print(f"[daisystardet] gate ERROR on cand={phi}: {e}", file=sys.stderr)
        return False


class DaisystarDet:
    """The deterministic anchored read-off as a `Translator` (`Language →
    LTLResult`). Constructed with the child labeler for exit targets. Applies to a
    rejecting initial SCC with a deterministic L-partition and at least one exit;
    declines otherwise. Holds no state."""

    name = _NAME

    def __init__(self, child: "Translator") -> None:
        self._child = child

    def __call__(self, lang: "Language") -> "LTLResult":
        aut = lang.tgba()
        if _TRACE:
            print("[daisystardet] in " + format_language(lang, aut), file=sys.stderr)
        h = aut.get_init_state_number()
        res = LTLResult.start(_NAME)

        si = spot.scc_info(aut)
        if not si.is_rejecting_scc(si.scc_of(h)):
            return _out(res.fail(Status.DECLINED, "initial SCC is not rejecting"))

        C = init_scc_states(aut, h)
        L, O, exits = scc_data(aut, C, h)
        if not any(exits[p] for p in C):
            return _out(res.fail(Status.DECLINED, "rejecting SCC with no exit (not reachability)"))
        if not is_deterministic(L, h):
            return _out(res.fail(Status.DECLINED, "L-partition is not deterministic"))

        # Delegate each distinct exit target to Λ; credit, bail on NOK.
        dsts: List[int] = [dst for p in C for _, dst in exits[p]]
        phi: Dict[int, "spot.formula"] = {}
        for dst in dict.fromkeys(dsts):
            sub = Language.of(reroot(aut, dst))
            if _TRACE:
                print(f"[daisystardet] delegating exit {dst} as language: "
                      + format_language(sub, sub.tgba()), file=sys.stderr)
            child = self._child(sub)
            # Fold the exit label in; a NotLTL child has its witness lifted back to the
            # hub by the reaching word h ⟶* p →(g) dst — `w[u ↦ w_dst·u]` — and
            # daisystardet credited (algorithm.md).
            res.prefix(child, "; ".join(exit_word(aut, C, h, dst)), _NAME)
            if res.nok:
                return _out(res)
            phi[dst] = child.formula

        cand = build_det_candidate(aut, C, h, L, O, exits, phi)
        if not _validates(aut, cand):
            return _out(res.fail(Status.DECLINED,
                            "candidate not language-equivalent "
                            "(daisystardet read-off rejected by gate)"))
        res.formula = cand
        return _out(res)
