"""The `daisy2` combinator Translator (see algorithm2.md).

`Daisy2(child)` peels a **length-1 star hub** — the initial state's SCC when it
is a hub `h` with petal self-loops, stem exits, and one-hop spokes (entry `h→s`,
optional self-loop body, return `s→h`) — generalizing `daisy` by one level. It
emits the daisy production lifted from single letters to **moves** (a petal, or a
spoke excursion `E_s ∧ X(G_s U R_s)`):

    Final = STAY∞ ∨ LEAVE
    STAY∞ = G(stay) ∧ ⋀_i GF(comp_i)
    LEAVE = stay U ⋁_j ( g_j ∧ X φ_j )

with `stay` the move-level stay-region (petal guards, spoke entries, spoke
bodies). The closed move-level form is **not yet solved** (algorithm2.md Open
points); `daisy2` therefore emits its current best candidate and adopts it
**only** if a Spot oracle finds it language-equivalent to the input — otherwise
it declines. So it is always sound; what we are measuring is how often the
candidate is complete. It is looser than `daisy` (a whole star SCC, not one
self-loop state) and declines when the SCC is not a length-1 star.
"""

from typing import List, TYPE_CHECKING

import spot

from aut2ltl.language import Language
from aut2ltl.result import LTLResult, Status
from .shape import Spoke, Stem, reroot, star_partition

if TYPE_CHECKING:
    from aut2ltl.translator import Translator

_NAME = "daisy2"
_F = spot.formula


def _or(fs: List["spot.formula"]) -> "spot.formula":
    """Disjunction of `fs`; the empty disjunction is `false`."""
    return _F.Or(fs) if fs else _F.ff()


def _and(fs: List["spot.formula"]) -> "spot.formula":
    """Conjunction of `fs`; the empty conjunction is `true`."""
    return _F.And(fs) if fs else _F.tt()


def _excursion(sp: "Spoke") -> "spot.formula":
    """The spoke move `D_s = E_s ∧ X(G_s U R_s)` — take the entry now, then loop
    on the body until the return fires. With no self-loop (`G_s = false`) this is
    `false U R_s ≡ R_s`, the rigid two-step detour `E_s ∧ X R_s`."""
    return _F.And([sp.entry, _F.X(_F.U(sp.body, sp.ret))])


def build_candidate(
    petals: List["Petal"], spokes: List["Spoke"], stems: List["Stem"],
    children: List["spot.formula"], m: int,
) -> "spot.formula":
    """The current best move-level candidate `STAY∞ ∨ LEAVE` (algorithm2.md). Free
    function so probes can inspect the exact formula daisy2 gates — the closed
    form is unsolved, so what it emits is the object under study."""
    # The move-level stay-region: a petal letter, a spoke move-start
    # (E_s ∧ X(G_s U R_s)), or an in-body residual (G_s U R_s). The last two
    # together cover entry positions and body positions of an excursion.
    sigma = _or([g for g, _ in petals])
    bodies = [_F.U(sp.body, sp.ret) for sp in spokes]
    excursions = [_excursion(sp) for sp in spokes]
    stay = _or([sigma] + excursions + bodies)

    # STAY∞ = G(stay) ∧ ⋀_i GF(comp_i). A mark is collected per edge ROLE, not
    # per spoke (algorithm2.md §Acceptance): entry/return edges fire on every
    # traversal (the bare excursion witnesses them), but a body self-loop mark
    # needs ≥ 1 real loop step — E_s ∧ X(G_s ∧ (G_s U R_s)).
    gfs: List["spot.formula"] = []
    for i in range(m):
        disj: List["spot.formula"] = [g for g, acc in petals if i in acc]
        for sp in spokes:
            if i in sp.entry_acc or i in sp.ret_acc:
                disj.append(_excursion(sp))
            if i in sp.body_acc:
                disj.append(_F.And([sp.entry,
                                    _F.X(_F.And([sp.body, _F.U(sp.body, sp.ret)]))]))
        gfs.append(_F.G(_F.F(_or(disj))))
    stay_inf = _and([_F.G(stay)] + gfs)

    # LEAVE = stay U ⋁_j ( g_j ∧ X φ_j )
    eps = _or([_F.And([g, _F.X(phi)]) for (g, _), phi in zip(stems, children)])
    leave = _F.U(stay, eps)

    return _F.Or([stay_inf, leave])


def _validates(aut: "spot.twa_graph", phi: "spot.formula") -> bool:
    """Soundness gate (the `partscc` pattern): adopt `φ` only if it is
    language-equivalent to the input `aut`. The unsolved closed form simply fails
    here when it is wrong, so daisy2 can never answer unsoundly."""
    try:
        cand = phi.translate("GeneralizedBuchi", "Small", "High")
        return spot.are_equivalent(aut, cand)
    except Exception:
        return False


class Daisy2:
    """The pure length-1 star-hub combinator `daisy2(Λ)` as a `Translator`
    (`Language → LTLResult`).

    Constructed with the child labeler `Λ` it uses for stem targets (the same
    decorator seam as `daisy`). It peels the initial SCC of the input Language's
    TGBA form when that SCC is a length-1 star hub, gates the candidate through a
    Spot oracle, and declines otherwise. Holds no state."""

    name = _NAME

    def __init__(self, child: "Translator") -> None:
        self._child = child

    def __call__(self, lang: "Language") -> "LTLResult":
        aut = lang.tgba()
        h = aut.get_init_state_number()
        res = LTLResult.start(_NAME)                    # start OK, credit ourselves

        parts = star_partition(aut, h)
        if parts is None:
            return res.fail(Status.DECLINED,
                            "initial SCC is not a length-1 star hub")
        petals, spokes, stems = parts
        m = aut.acc().num_sets()

        # Delegate each stem to Λ; credit it in, bail on NOK (propagating reason).
        children: List["spot.formula"] = []
        for _, dst in stems:
            child = self._child(Language.of(reroot(aut, dst)))
            res.credit(child)
            if res.nok:
                return res
            children.append(child.formula)

        phi = build_candidate(petals, spokes, stems, children, m)
        if not _validates(aut, phi):
            return res.fail(Status.DECLINED,
                            "candidate not language-equivalent "
                            "(daisy2 closed form incomplete for this SCC)")
        res.formula = phi
        return res
