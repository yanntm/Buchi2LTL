"""The `daisy` combinator Translator (see algorithm.md).

`Daisy(child)` peels a **single daisy** — the initial state of the input Language's
TGBA form when that state is a daisy (its only incoming edges are self-loops) — and
emits the closed-form LTL of the language accepted from it:

    Final(q) = STAY∞(q) ∨ LEAVE(q)
    STAY∞(q) = G(σ) ∧ ⋀_{i<m} GF(σ_i)            -- stay forever, accepting
    LEAVE(q) = σ U ⋁_j ( g_j ∧ X φ_j )           -- stay finitely, then exit

with `σ` the petal guards, `σ_i` the petals carrying acc set `i`, and `φ_j` the
child's label of stem `j`. It declines when `q` is not a daisy, and a single declined
child poisons `q`. A **local, context-free production**: it inspects one state's own
edges and treats each stem target's label as an opaque sub-term handed to it by the
child. It does not recurse and owns no global concern (termination, well-foundedness
of the child) — those belong to the assembly that wires the child. See algorithm.md.
"""

import os
import sys
from typing import List, TYPE_CHECKING

import spot

from aut2ltl.language import Language
from aut2ltl.verifier import revalidated
from aut2ltl.result import LTLResult, Status
from aut2ltl.printer import format_language, format_result
from .shape import is_daisy, reroot, split

if TYPE_CHECKING:
    from aut2ltl.translator import Translator

_NAME = "daisy"
_F = spot.formula

# On when either DAISY_TRACE or the global TRANSLATOR_TRACE_ON is set (presence;
# value ignored). Every message is built inside `if _TRACE:`, so nothing is computed
# when off.
_TRACE = "DAISY_TRACE" in os.environ or "TRANSLATOR_TRACE_ON" in os.environ


def _out(res: "LTLResult") -> "LTLResult":
    """Trace the outgoing result (status / size), pass it through unchanged."""
    if _TRACE:
        print("[daisy] out " + format_result(res), file=sys.stderr)
    return res


def _or(fs: List["spot.formula"]) -> "spot.formula":
    """Disjunction of `fs`; the empty disjunction is `false`."""
    return _F.Or(fs) if fs else _F.ff()


def _and(fs: List["spot.formula"]) -> "spot.formula":
    """Conjunction of `fs`; the empty conjunction is `true`."""
    return _F.And(fs) if fs else _F.tt()


class Daisy:
    """The pure daisy combinator `daisy(Λ)` as a `Translator` (`Language →
    LTLResult`).

    Constructed with the child labeler `Λ` it uses for exit targets (the decorator
    seam). It peels the initial state of the input Language's TGBA form when that
    state is a daisy, and declines otherwise — see `algorithm.md`. Holds no state."""

    name = _NAME

    def __init__(self, child: "Translator") -> None:
        self._child = child

    def __call__(self, lang: "Language") -> "LTLResult":
        aut = lang.tgba()
        if _TRACE:
            print("[daisy] in " + format_language(lang, aut), file=sys.stderr)
        q = aut.get_init_state_number()
        res = LTLResult.start(_NAME)                   # start OK, credit ourselves

        # Accept iff q is a daisy (only self-loops come back to it).
        if not is_daisy(aut, q):
            return _out(res.fail(Status.DECLINED, "initial state is not a daisy"))

        m = aut.acc().num_sets()
        petals, stems = split(aut, q)

        # Delegate each stem to Λ; fold it in, bail on NOK (propagating reason).
        # A NotLTL child certifies the residue past the stem non-LTL, hence L too (the
        # residue is the left quotient g⁻¹L); `prefix` lifts its witness back up the
        # stem by the guard g — `w[u ↦ g·u]` — and credits daisy (algorithm.md).
        children: List["spot.formula"] = []
        for g, dst in stems:
            sub = Language.of(reroot(aut, dst))
            if _TRACE:
                print(f"[daisy] delegating exit {dst} as language: "
                      + format_language(sub, sub.tgba()), file=sys.stderr)
            child = self._child(sub)
            res.prefix(child, str(g), _NAME)
            if res.nok:
                # A lifted NOT_LTL is kept only if its family replays against THIS
                # language (the quotient lift needs exactness the guard may lack);
                # else it degrades to a decline (witness/algorithm.md, Lifting).
                return _out(revalidated(res, lang))
            children.append(child.formula)

        sigma = _or([g for g, _ in petals])

        # STAY∞(q) = G(σ) ∧ ⋀_{i<m} GF(σ_i)
        gfs = [_F.G(_F.F(_or([g for g, acc in petals if i in acc]))) for i in range(m)]
        stay = _and([_F.G(sigma)] + gfs)

        # LEAVE(q) = σ U ⋁_j ( g_j ∧ X φ_j )
        eps = _or([_F.And([g, _F.X(phi)]) for (g, _), phi in zip(stems, children)])
        leave = _F.U(sigma, eps)

        res.formula = _F.Or([stay, leave])             # finish: fill the formula
        return _out(res)
