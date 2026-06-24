"""The `Roundtrip` combinator Translator (see algorithm.md).

`Roundtrip(labeler)` labels a Language with `labeler`, re-describes the language by
the resulting formula, and labels that re-description with `labeler` again — returning
the second result. A declined first label propagates unchanged. Constructed with the
child `labeler` Translator it applies on both ends.
"""

from typing import TYPE_CHECKING

from aut2ltl.language import Language, UntranslatableLanguage
from aut2ltl.result import LTLResult

if TYPE_CHECKING:
    from aut2ltl.translator import Translator

_NAME = "roundtrip"


class Roundtrip:
    """A `Translator` (`Language → LTLResult`) that re-derives its answer through one
    formula round trip: label with `labeler`, rebuild a Language from that formula,
    label that again.

    Constructed with the child `labeler` it applies on both ends; holds no other
    state."""

    name = _NAME

    def __init__(self, labeler: "Translator") -> None:
        self._labeler = labeler

    def __call__(self, lang: "Language") -> "LTLResult":
        res = LTLResult.start(_NAME)                   # start OK, credit ourselves

        # SEED: label the input; fold its work in. A NOK seed leaves nothing to
        # re-describe — bail with its reason intact.
        seed = self._labeler(lang)
        res.credit(seed)
        if res.nok:
            return res

        # RE-DESCRIBE + RELABEL: rebuild the Language from the seed formula, label it
        # again, fold that in. A NOK relabel bails with its reason intact. If the seed
        # is too large for ltl2tgba — the floor raises `UntranslatableLanguage` rather
        # than blow Spot up — the reshape is simply unavailable: DECLINE (the sound
        # bottom), so an outer `best_of` keeps the plain arm. Never a wrong answer.
        try:
            relabel = self._labeler(Language.of_ltl(seed.formula))
        except UntranslatableLanguage:
            return LTLResult.decline()
        res.credit(relabel)
        if res.nok:
            return res

        res.formula = relabel.formula                  # finish: the re-derivation IS the formula
        return res
