"""aut2ltl/result.py — the Translator result and its lifecycle algebra.

Faithful implementation of `result.md`. A `Result` is the value a `Translator`
returns; `Status` is its closed three-value state. Two algebras combine results:

  * composition — `credit` / `fuse`: the OK-identity monoid (a child's work is
    folded in; the worst status wins). Used as a per-call accumulator.
  * choice — `first` / `decline`: the decline-identity monoid (try translators in
    order; the first non-declined wins; a NOT_LTL verdict short-circuits).

See `result.md` for the model, the two-state OK/NOK consumer view, and the duality.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, FrozenSet, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    import spot
    from aut2ltl.language import Language


class Status(Enum):
    """Closed result state.

    OK       — success; carries a formula.
    DECLINED — the translator was unable to produce a result (recoverable: `first`
               tries the next member).
    NOT_LTL  — the language is not LTL-definable (absorbing verdict). Whether this
               is a proof or a strong hint is stated in the diagnosis, not here.
    """
    OK = "OK"
    DECLINED = "DECLINED"
    NOT_LTL = "NOT_LTL"


# Dominance order for composition (credit/fuse): the worst status wins.
_RANK = {Status.OK: 0, Status.DECLINED: 1, Status.NOT_LTL: 2}


class Result:
    """A Translator's result: a formula (only when OK), the contributing technique
    tags, a status, and an optional diagnosis.

    Used as a per-call accumulator (see `result.md` "Usage"): start OK crediting
    yourself, `credit` each delegate in, bail returning self on NOK, else fill the
    `formula` and return. The accumulator is never shared, so the mutation is safe.
    """

    __slots__ = ("_status", "_formula", "_technique", "_diagnosis")

    def __init__(
        self,
        status: "Status",
        formula: Optional["spot.formula"] = None,
        technique: Optional[Set[str]] = None,
        diagnosis: Optional[str] = None,
    ) -> None:
        self._status = status
        self._formula = formula
        self._technique: Set[str] = set(technique) if technique else set()
        self._diagnosis = diagnosis

    # --- factories -------------------------------------------------------------
    @classmethod
    def start(cls, *techniques: str) -> "Result":
        """The accumulator seed: an OK result with no formula yet, credited with
        your own technique tag(s)."""
        return cls(Status.OK, technique=set(techniques))

    @classmethod
    def success(cls, formula: "spot.formula", *techniques: str) -> "Result":
        """A finished OK result carrying its formula (the leaf-producer shape)."""
        return cls(Status.OK, formula=formula, technique=set(techniques))

    @classmethod
    def decline(cls, diagnosis: Optional[str] = None, *techniques: str) -> "Result":
        """A DECLINED result (recoverable). Optional diagnosis."""
        return cls(Status.DECLINED, technique=set(techniques), diagnosis=diagnosis)

    @classmethod
    def not_definable(cls, diagnosis: Optional[str] = None, *techniques: str) -> "Result":
        """A NOT_LTL verdict (absorbing). The diagnosis may note proof vs hint."""
        return cls(Status.NOT_LTL, technique=set(techniques), diagnosis=diagnosis)

    # --- queries ---------------------------------------------------------------
    @property
    def status(self) -> "Status":
        return self._status

    @property
    def ok(self) -> bool:
        return self._status is Status.OK

    @property
    def nok(self) -> bool:
        return self._status is not Status.OK

    @property
    def declined(self) -> bool:
        return self._status is Status.DECLINED

    @property
    def not_ltl(self) -> bool:
        return self._status is Status.NOT_LTL

    @property
    def technique(self) -> FrozenSet[str]:
        return frozenset(self._technique)

    @property
    def diagnosis(self) -> Optional[str]:
        return self._diagnosis

    @property
    def formula(self) -> Optional["spot.formula"]:
        return self._formula

    @formula.setter
    def formula(self, f: "spot.formula") -> None:
        self._formula = f

    def technique_str(self) -> str:
        return "+".join(sorted(self._technique)) if self._technique else "-"

    # --- composition monoid ----------------------------------------------------
    def credit(self, other: "Result") -> "Result":
        """Fold a child result in (mutates and returns self). An OK child
        contributes its techniques; a more-dominant NOK child flips this result to
        that status (accumulating its diagnosis, clearing the formula)."""
        if other.ok:
            self._technique |= set(other.technique)
            return self
        # other is NOK: raise to the worse status (NOT_LTL ≻ DECLINED), clearing
        # the formula, and ACCUMULATE its diagnosis (a NOK fused with a NOK
        # inherits both reasons).
        other_status = Status.NOT_LTL if other.not_ltl else Status.DECLINED
        if _RANK[other_status] > _RANK[self._status]:
            self._status = other_status
            self._formula = None
        self._add_diagnosis(other.diagnosis)
        return self

    def fail(self, status: "Status", diagnosis: Optional[str] = None) -> "Result":
        """Transition this result to a NOK status, accumulating an optional
        diagnosis (clears the formula). Returns self."""
        assert status is not Status.OK, "fail() needs a NOK status"
        self._status = status
        self._formula = None
        self._add_diagnosis(diagnosis)
        return self

    def _add_diagnosis(self, diagnosis: Optional[str]) -> None:
        if diagnosis:
            self._diagnosis = "; ".join(p for p in (self._diagnosis, diagnosis) if p)

    def __repr__(self) -> str:
        return (f"Result({self._status.value}, formula={self._formula}, "
                f"technique={sorted(self._technique)}, diagnosis={self._diagnosis!r})")


def fuse(primary: "Result", *others: "Result") -> "Result":
    """Credit several children into `primary` (the composition monoid, folded)."""
    for other in others:
        primary.credit(other)
    return primary


# --- choice monoid -------------------------------------------------------------
def decline(_lang: "Language") -> "Result":
    """The identity translator: always a bare DECLINED — `first`'s terminal/unit."""
    return Result.decline()


def first(*translators: Callable[["Language"], "Result"]) -> Callable[["Language"], "Result"]:
    """Choice monoid: try `translators` in order, return the first non-declined
    result (OK or NOT_LTL — a verdict short-circuits); a DECLINED falls through to
    the next. The terminal (all declined / empty) is a bare decline."""
    members: List[Callable[["Language"], "Result"]] = list(translators)

    def run(lang: "Language") -> "Result":
        for t in members:
            r = t(lang)
            if not r.declined:        # OK or NOT_LTL: return as-is (reason kept)
                return r
        return Result.decline()
    return run
