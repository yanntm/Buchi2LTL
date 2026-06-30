"""The `daisystar` combinator Translator (see algorithm.md).

`Daisystar(child)` peels the initial state's SCC when it is a **rejecting**
length-1 star hub — a hub with petal self-loops, hub-stems, and one-hop spokes
that may themselves exit `C` — i.e. the *reachability* dual of `daisy2`. Because
the SCC is rejecting (Spot tags it), no run that stays in `C` forever accepts, so

    STAY∞ = false      (sound by construction — no oracle, no flat-G safety form)

and the whole language is the least-fixpoint `LEAVE`: finitely many stay-moves
(a petal `σ`, or a return excursion `E_s ∧ X(G_s U R_s)`), then an exit move to a
child — a hub-stem `g_j ∧ X φ_j` or a **spoke-exit** `E_s ∧ X(G_s U (h_k ∧ X φ_k))`.

    Final = LEAVE = stay U ⋁(exit moves)

This sidesteps daisy2's open `Φ_stay` math entirely (its hard half is identically
`false` here). The `LEAVE` body still carries daisy2's flat stay-region, so the
candidate is adopted **only** if a Spot oracle finds it language-equivalent to the
input — otherwise daisystar declines. Always sound; what we measure is coverage.
"""

import os
import sys
from typing import Dict, List, TYPE_CHECKING

import spot

from aut2ltl.language import Language
from aut2ltl.result import LTLResult, Status
from .shape import Spoke, Stem, star_partition, reroot

if TYPE_CHECKING:
    from aut2ltl.translator import Translator

_NAME = "daisystar"
_F = spot.formula

# Dev trace of the Spot equivalence gate, mirroring daisy2's DAISY2_TRACE; the
# global TRANSLATOR_TRACE_ON lights it (and every translator trace) at once. Every
# use guards with `if _TRACE:` BEFORE building its message, so a formula is never
# flattened for a trace that will not be printed.
_TRACE = "DAISYSTAR_TRACE" in os.environ or "TRANSLATOR_TRACE_ON" in os.environ


def _or(fs: List["spot.formula"]) -> "spot.formula":
    """Disjunction of `fs`; the empty disjunction is `false`."""
    return _F.Or(fs) if fs else _F.ff()


def _excursion(sp: "Spoke") -> "spot.formula":
    """The return excursion `E_s ∧ X(G_s U R_s)` — a stay-move: enter the spoke,
    loop on the body until the return fires (back at the hub)."""
    return _F.And([sp.entry, _F.X(_F.U(sp.body, sp.ret))])


def _spoke_exit(sp: "Spoke", guard: "spot.formula",
                phi: "spot.formula") -> "spot.formula":
    """The leave-via-spoke move `E_s ∧ X(G_s U (h_k ∧ X φ_k))` — enter the spoke,
    loop on the body until the spoke-stem `h_k` fires, handing control to the
    child label `φ_k`. With no body (`G_s = false`) this collapses to
    `E_s ∧ X(h_k ∧ X φ_k)`, the rigid enter-then-exit detour."""
    return _F.And([sp.entry, _F.X(_F.U(sp.body, _F.And([guard, _F.X(phi)])))])


def build_leave(
    petals: List["spot.formula"], spokes: List["Spoke"],
    hub_stems: List["Stem"], child_of: Dict[int, "spot.formula"],
) -> "spot.formula":
    """The reachability label `LEAVE = stay U ⋁(exit moves)` (algorithm.md). Free
    function so probes can inspect the exact formula daisystar gates. `child_of`
    maps each exit's destination state to its child label."""
    # Move-level stay-region (same flat form as daisy2's LEAVE): a petal letter, a
    # return excursion (E_s ∧ X(G_s U R_s)), or an in-body residual (G_s U R_s) so
    # the per-position `U` holds while the run is mid-excursion. Its looseness is
    # what the Spot gate nets.
    sigma = _or(petals)
    excursions = [_excursion(sp) for sp in spokes]
    bodies = [_F.U(sp.body, sp.ret) for sp in spokes]
    stay = _or([sigma] + excursions + bodies)

    exits: List["spot.formula"] = []
    for g, dst in hub_stems:
        exits.append(_F.And([g, _F.X(child_of[dst])]))
    for sp in spokes:
        for g, dst in sp.stems:
            exits.append(_spoke_exit(sp, g, child_of[dst]))

    return _F.U(stay, _or(exits))


def _trace_reject(aut: "spot.twa_graph", phi: "spot.formula",
                  cand: "spot.twa_graph") -> None:
    """Trace one gate REJECT with a containment witness each way (too loose / too
    tight). Witnesses are bounded — the star automata are tiny."""
    try:
        loose = cand.intersecting_word(spot.complement(aut))   # cand \ input
        tight = aut.intersecting_word(spot.complement(cand))   # input \ cand
    except Exception as e:
        loose = tight = f"<witness error: {e}>"
    print(f"[daisystar] gate REJECT: cand={phi}", file=sys.stderr)
    print(f"[daisystar]     too loose (cand\\input): {loose}", file=sys.stderr)
    print(f"[daisystar]     too tight (input\\cand): {tight}", file=sys.stderr)


def _validates(aut: "spot.twa_graph", phi: "spot.formula") -> bool:
    """Soundness gate (the `partscc`/`daisy2` pattern): adopt `φ` only if it is
    language-equivalent to the input `aut`. STAY∞=false is sound by construction;
    this nets the residual looseness of the flat `LEAVE` stay-region."""
    try:
        cand = phi.translate("GeneralizedBuchi", "Small", "High")
        if spot.are_equivalent(aut, cand):
            return True
        if _TRACE:
            _trace_reject(aut, phi, cand)
        return False
    except Exception as e:
        if _TRACE:
            print(f"[daisystar] gate ERROR on cand={phi}: {e}", file=sys.stderr)
        return False


class Daisystar:
    """The rejecting length-1 star-hub combinator `daisystar(Λ)` as a `Translator`
    (`Language → LTLResult`).

    Constructed with the child labeler `Λ` for exit targets (the same decorator
    seam as `daisy`/`daisy2`). It peels the initial SCC when that SCC is rejecting
    and a length-1 star, gates the `LEAVE` candidate through a Spot oracle, and
    declines otherwise. Holds no state."""

    name = _NAME

    def __init__(self, child: "Translator") -> None:
        self._child = child

    def __call__(self, lang: "Language") -> "LTLResult":
        aut = lang.tgba()
        h = aut.get_init_state_number()
        res = LTLResult.start(_NAME)                    # start OK, credit ourselves

        # The reachability regime: the initial SCC must be REJECTING (no accepting
        # cycle stays inside it), which makes STAY∞ = false sound. Spot tags it.
        si = spot.scc_info(aut)
        if not si.is_rejecting_scc(si.scc_of(h)):
            return res.fail(Status.DECLINED,
                            "initial SCC is not rejecting (not the reachability regime)")

        parts = star_partition(aut, h)
        if parts is None:
            return res.fail(Status.DECLINED,
                            "initial SCC is not a length-1 star hub")
        petals, spokes, hub_stems = parts

        # Delegate every exit target (hub-stems and spoke-stems) to Λ once per
        # distinct destination; credit it in, bail on NOK (propagating reason).
        dsts: List[int] = [dst for _, dst in hub_stems]
        dsts += [dst for sp in spokes for _, dst in sp.stems]
        child_of: Dict[int, "spot.formula"] = {}
        for dst in dict.fromkeys(dsts):                 # unique, order-preserving
            child = self._child(Language.of(reroot(aut, dst)))
            res.credit(child)
            if res.nok:
                return res
            child_of[dst] = child.formula

        phi = build_leave(petals, spokes, hub_stems, child_of)
        if not _validates(aut, phi):
            return res.fail(Status.DECLINED,
                            "candidate not language-equivalent "
                            "(daisystar LEAVE form incomplete for this SCC)")
        res.formula = phi
        return res
