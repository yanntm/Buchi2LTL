"""The `daisy2` combinator Translator (see algorithm.md).

`Daisy2(child)` peels a **length-1 star hub** — the initial state's SCC when it
is a hub `h` with petal self-loops, stem exits, and one-hop spokes (entry `h→s`,
optional self-loop body, return `s→h`) — generalizing `daisy` by one level. It
emits the daisy production lifted from single letters to **moves** (a petal, or a
spoke excursion `E_s ∧ X(G_s U R_s)`):

    Final = STAY∞ ∨ LEAVE
    STAY∞ = G(stay) ∧ ⋀_i GF(comp_i)
    LEAVE = stay U ⋁_j ( g_j ∧ X φ_j )

with `stay` the move-level stay-region (petal guards, spoke entries, spoke
bodies). The closed move-level form is **not yet solved** (algorithm.md Open
points); `daisy2` therefore emits its current best candidate and adopts it
**only** if a Spot oracle finds it language-equivalent to the input — otherwise
it declines. So it is always sound; what we are measuring is how often the
candidate is complete. It is looser than `daisy` (a whole star SCC, not one
self-loop state) and declines when the SCC is not a length-1 star.
"""

import os
import sys
from typing import List, TYPE_CHECKING

import spot

from aut2ltl.language import Language
from aut2ltl.result import LTLResult, Status
from aut2ltl.printer import format_language, format_result
from .shape import Spoke, Stem, reroot, star_partition

if TYPE_CHECKING:
    from aut2ltl.translator import Translator

_NAME = "daisy2"
_F = spot.formula

# Dev trace of the Spot equivalence gate, mirroring the bls KR_TRACE convention
# (an env-scoped module flag, not an Options knob — tracing is process-scoped, see
# TODO.md "Deferred"). When DAISY2_TRACE — or the global TRANSLATOR_TRACE_ON, which
# lights every translator trace at once — is on, every gate REJECT prints the
# rejected candidate and a containment witness in each direction, so the closed
# form's incompleteness is visible in a run. To stderr: the formula is on stdout.
# Every use guards with `if _TRACE:` BEFORE building its message, so a formula is
# never flattened for a trace that will not be printed.
_TRACE = (os.getenv("DAISY2_TRACE", "0").lower() in ("1", "true", "yes", "on")
          or "TRANSLATOR_TRACE_ON" in os.environ)


def _out(res: "LTLResult") -> "LTLResult":
    """Trace the outgoing result (status / size), pass it through unchanged."""
    if _TRACE:
        print("[daisy2] out " + format_result(res), file=sys.stderr)
    return res


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
    """The current best move-level candidate `STAY∞ ∨ LEAVE` (algorithm.md). Free
    function so probes can inspect the exact formula daisy2 gates — the closed
    form is unsolved, so what it emits is the object under study."""
    # The move-level stay-region: a petal letter, a spoke move-start
    # (E_s ∧ X(G_s U R_s)), or an in-body residual (G_s U R_s). The last two
    # together cover entry positions and body positions of an excursion.
    sigma = _or([g for g, _ in petals])
    bodies = [_F.U(sp.body, sp.ret) for sp in spokes]
    excursions = [_excursion(sp) for sp in spokes]
    stay = _or([sigma] + excursions + bodies)

    # STAY∞ = G(stay) ∧ ⋀_i GF(comp_i): the per-edge GF anchor at the move boundary
    # (algorithm.md §Acceptance). Under S3 marks sit only on petals and the
    # entry/return links, each taken once per move, so comp_i credits only the
    # i-MARKED sibling of a role (E_s^i / R_s^i) — never the unmarked parallel
    # edges, and there is no body case.
    gfs: List["spot.formula"] = []
    for i in range(m):
        disj: List["spot.formula"] = [g for g, marks in petals if i in marks]
        for sp in spokes:
            ent_i = [g for g, marks in sp.entries if i in marks]   # E_s^i
            ret_i = [g for g, marks in sp.rets if i in marks]      # R_s^i
            if ent_i:
                disj.append(_F.And([_or(ent_i), _F.X(_F.U(sp.body, sp.ret))]))
            if ret_i:
                disj.append(_F.And([sp.entry, _F.X(_F.U(sp.body, _or(ret_i)))]))
        gfs.append(_F.G(_F.F(_or(disj))))
    stay_inf = _and([_F.G(stay)] + gfs)

    # LEAVE = stay U ⋁_j ( g_j ∧ X φ_j )
    eps = _or([_F.And([g, _F.X(phi)]) for (g, _), phi in zip(stems, children)])
    leave = _F.U(stay, eps)

    return _F.Or([stay_inf, leave])


def _trace_reject(aut: "spot.twa_graph", phi: "spot.formula",
                  cand: "spot.twa_graph") -> None:
    """Trace one gate REJECT with a containment witness in each direction (the
    closed form too loose / too tight). Witnesses are bounded — the star automata
    are tiny — and computed only under the trace flag."""
    try:
        loose = cand.intersecting_word(spot.complement(aut))   # cand \ input
        tight = aut.intersecting_word(spot.complement(cand))   # input \ cand
    except Exception as e:
        loose = tight = f"<witness error: {e}>"
    print(f"[daisy2] gate REJECT: cand={phi}", file=sys.stderr)
    print(f"[daisy2]     too loose (cand\\input): {loose}", file=sys.stderr)
    print(f"[daisy2]     too tight (input\\cand): {tight}", file=sys.stderr)


def _validates(aut: "spot.twa_graph", phi: "spot.formula") -> bool:
    """Soundness gate (the `partscc` pattern): adopt `φ` only if it is
    language-equivalent to the input `aut`. The unsolved closed form simply fails
    here when it is wrong, so daisy2 can never answer unsoundly. A REJECT (or a
    Spot error) is traced under DAISY2_TRACE so gate failures are visible."""
    try:
        cand = phi.translate("GeneralizedBuchi", "Small", "High")
        if spot.are_equivalent(aut, cand):
            if _TRACE:
                print("[daisy2] gate PASS", file=sys.stderr)
            return True
        if _TRACE:
            _trace_reject(aut, phi, cand)
        return False
    except Exception as e:
        if _TRACE:
            print(f"[daisy2] gate ERROR on cand={phi}: {e}", file=sys.stderr)
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
        if _TRACE:
            print("[daisy2] in " + format_language(lang, aut), file=sys.stderr)
        h = aut.get_init_state_number()
        res = LTLResult.start(_NAME)                    # start OK, credit ourselves

        parts = star_partition(aut, h)
        if parts is None:
            return _out(res.fail(Status.DECLINED,
                                 "initial SCC is not a length-1 star hub"))
        petals, spokes, stems = parts
        m = aut.acc().num_sets()

        # Delegate each stem to Λ; credit it in, bail on NOK (propagating reason).
        children: List["spot.formula"] = []
        for _, dst in stems:
            child = self._child(Language.of(reroot(aut, dst)))
            res.credit(child)
            if res.nok:
                return _out(res)
            children.append(child.formula)

        phi = build_candidate(petals, spokes, stems, children, m)
        if not _validates(aut, phi):
            return _out(res.fail(Status.DECLINED,
                                 "candidate not language-equivalent "
                                 "(daisy2 closed form incomplete for this SCC)"))
        res.formula = phi
        return _out(res)
