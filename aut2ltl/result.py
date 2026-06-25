"""aut2ltl/result.py — the value a Translator returns, and how results combine.

A Translator yields more than a formula: which method produced it, and whether it
succeeded, declined, or proved the language non-LTL. `LTLResult` carries all of it —
a `Status`, the `formula` (only when OK), the contributing `technique` tags, an
optional `diagnosis`, and — on a NOT_LTL verdict — an optional `witness` (the counting
family certifying non-definability) — so composition stays sound and self-reporting (a
bare `spot.formula` hid which method fired, and could not distinguish "not my case"
from "impossible").

`Status` is closed and three-valued:
  * OK       — success; `.formula` is language-equivalent to the input.
  * DECLINED — this translator cannot handle the input (recoverable: try another).
  * NOT_LTL  — the language is not LTL-definable (absorbing verdict; no method wins).

Results combine by two monoids:
  * composition — `credit` / `fuse`: fold a child's work in; the worst status wins
    (NOT_LTL ≻ DECLINED ≻ OK), techniques union, diagnoses accumulate, a NOT_LTL
    child's witness rides up; OK is the unit.
  * choice — `first` / `decline`: try translators in order, take the first non-declined
    result (NOT_LTL short-circuits); DECLINED falls through; `decline` is the unit.

Usage — the accumulator idiom. A translator threads ONE result:

    res = LTLResult.start(MY_TAG)        # OK seed, credited with your own tag
    for child in children:
        res.credit(child(...))           # fold each delegate in
        if res.nok:                      # bail on the first NOK, reason intact
            return res
    res.formula = build(...)             # finish: fill the formula
    return res                           # (on error: res.fail(NOT_LTL, why))

The accumulator is per-call (never shared), so the mutation is safe.

NOT FINAL: `LTLResult` is expected to trace/accumulate more over time (finer
provenance, a step trace). Route every child through `credit`/`fuse` rather than
lifting out its `.formula` alone — bypassing the idiom silently drops accumulated
metadata that a consumer above, or a field added later, will rely on. (Output SIZE is
deliberately NOT a field here: it is derived from `.formula` by whoever needs it —
the `best_of` comparators — keeping the contract floor free of the metric layer.)
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, FrozenSet, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    import spot
    from aut2ltl.language import Language
    from aut2ltl.witness import Witness


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


class LTLResult:
    """A Translator's result: a formula (only when OK), the contributing technique
    tags, a status, and an optional diagnosis.

    Used as a per-call accumulator (see the module docstring "Usage"): start OK
    crediting yourself, `credit` each delegate in, bail returning self on NOK, else
    fill the `formula` and return. The accumulator is never shared, so mutation is safe.
    """

    __slots__ = ("_status", "_formula", "_technique", "_diagnosis", "_witness")

    def __init__(
        self,
        status: "Status",
        formula: Optional["spot.formula"] = None,
        technique: Optional[Set[str]] = None,
        diagnosis: Optional[str] = None,
        witness: Optional["Witness"] = None,
    ) -> None:
        self._status = status
        self._formula = formula
        self._technique: Set[str] = set(technique) if technique else set()
        self._diagnosis = diagnosis
        self._witness = witness

    # --- factories -------------------------------------------------------------
    @classmethod
    def start(cls, *techniques: str) -> "LTLResult":
        """The accumulator seed: an OK result with no formula yet, credited with
        your own technique tag(s)."""
        return cls(Status.OK, technique=set(techniques))

    @classmethod
    def success(cls, formula: "spot.formula", *techniques: str) -> "LTLResult":
        """A finished OK result carrying its formula (the leaf-producer shape)."""
        return cls(Status.OK, formula=formula, technique=set(techniques))

    @classmethod
    def decline(cls, diagnosis: Optional[str] = None, *techniques: str) -> "LTLResult":
        """A DECLINED result (recoverable). Optional diagnosis."""
        return cls(Status.DECLINED, technique=set(techniques), diagnosis=diagnosis)

    @classmethod
    def not_definable(
        cls,
        diagnosis: Optional[str] = None,
        *techniques: str,
        witness: Optional["Witness"] = None,
    ) -> "LTLResult":
        """A NOT_LTL verdict (absorbing). The diagnosis may note proof vs hint; the
        optional `witness` is the counting family certifying non-definability. This is
        the sole place a witness enters a result — `credit` only propagates it."""
        return cls(
            Status.NOT_LTL, technique=set(techniques), diagnosis=diagnosis, witness=witness
        )

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
    def witness(self) -> Optional["Witness"]:
        """The non-LTL counting family, when this verdict carries one (set only via
        the `not_definable` factory; `credit` carries a child's up)."""
        return self._witness

    @property
    def formula(self) -> Optional["spot.formula"]:
        return self._formula

    @formula.setter
    def formula(self, f: "spot.formula") -> None:
        self._formula = f

    def technique_str(self) -> str:
        return "+".join(sorted(self._technique)) if self._technique else "-"

    # --- composition monoid ----------------------------------------------------
    def credit(self, other: "LTLResult") -> "LTLResult":
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
        # a NOT_LTL child's witness rides up (first one wins; never clobbered)
        if self._witness is None and other.witness is not None:
            self._witness = other.witness
        return self

    def fail(self, status: "Status", diagnosis: Optional[str] = None) -> "LTLResult":
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
        return (f"LTLResult({self._status.value}, formula={self._formula}, "
                f"technique={sorted(self._technique)}, diagnosis={self._diagnosis!r}, "
                f"witness={self._witness!r})")


def fuse(primary: "LTLResult", *others: "LTLResult") -> "LTLResult":
    """Credit several children into `primary` (the composition monoid, folded)."""
    for other in others:
        primary.credit(other)
    return primary


# --- choice monoid -------------------------------------------------------------
def decline(_lang: "Language") -> "LTLResult":
    """The identity translator: always a bare DECLINED — `first`'s terminal/unit."""
    return LTLResult.decline()


def first(*translators: Callable[["Language"], "LTLResult"]) -> Callable[["Language"], "LTLResult"]:
    """Choice monoid: try `translators` in order, return the first non-declined
    result (OK or NOT_LTL — a verdict short-circuits); a DECLINED falls through to
    the next. The terminal (all declined / empty) is a bare decline."""
    members: List[Callable[["Language"], "LTLResult"]] = list(translators)

    def run(lang: "Language") -> "LTLResult":
        for t in members:
            r = t(lang)
            if not r.declined:        # OK or NOT_LTL: return as-is (reason kept)
                return r
        return LTLResult.decline()
    return run
