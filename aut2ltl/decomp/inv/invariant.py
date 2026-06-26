"""The `inv` Translator decorator (see algorithm.md).

`Invariant(child)` factors the global safety invariant `Σ = ⋁(edge guards)` out of
the input Language, delegates the *simplified* Language to `child`, and re-asserts
`G(Σ)` on `child`'s formula. It is defined entirely against the Translator contract:
it asks the Language for its TGBA, calls `child` once, and combines — it assumes
nothing about what `child` is.

The exact factorization `L(A) = L(strip(A,Σ)) ∩ L(G Σ)` makes this sound for one
application: the strip and the re-assertion of `G(Σ)` sit at the same Language
boundary around the same `child` call, so `child` always receives a self-consistent
language no matter what it does with it.
"""

from typing import TYPE_CHECKING

import spot
import buddy

from aut2ltl.language import Language
from aut2ltl.result import LTLResult
from .strip import sigma, strip

if TYPE_CHECKING:
    from aut2ltl.translator import Translator

_NAME = "inv"
_F = spot.formula


class Invariant:
    """The invariant-layer decorator as a `Translator` (`Language → LTLResult`).

    Constructed with the `child` labeler it strengthens (the decorator seam). Holds
    no state; create one per wiring."""

    name = _NAME

    def __init__(self, child: "Translator") -> None:
        self._child = child

    def __call__(self, lang: "Language") -> "LTLResult":
        aut = lang.tgba()
        sig = sigma(aut)

        # Vacuous (Σ ≡ true): G(true) carries nothing — pass the child's result
        # through unchanged, with no inv credit (inv did not act).
        if sig == buddy.bddtrue:
            return self._child(lang)

        # No-op strip: if restricting every guard under Σ leaves the automaton
        # unchanged (the stripped Language interns to the SAME object as the input
        # automaton's — identity by normalized-HOA, see language._intern), then the
        # child already sees the full language and `child.formula ⊨ G(Σ)`, so
        # re-asserting `G(Σ)` is pure redundancy (the obligation.ltl:5 bloat). Pass
        # through, no inv credit, as in the vacuous case — inv only earns its keep
        # when the strip actually simplifies. (Fail-safe if interning is off: the
        # `is` is then always False, so we keep the sound-but-redundant G.)
        stripped = Language.of(strip(aut, sig))
        if stripped is Language.of(aut):
            return self._child(lang)

        # Build/accumulate idiom (see result.py): seed an OK accumulator crediting
        # ourselves, delegate the stripped language, and credit the child IN — so
        # all of its fields (technique, diagnosis, and any future step-trace /
        # profiling info) flow through the contract instead of being hand-copied.
        res = LTLResult.start(_NAME)
        child = self._child(stripped)
        res.credit(child)
        if res.nok:
            return res                         # child declined / verdict: carried out

        # OK: re-assert the invariant on the child's formula (no re-instantiation).
        sig_f = spot.bdd_to_formula(sig, aut.get_dict())
        res.formula = _F.And([child.formula, _F.G(sig_f)])
        return res
