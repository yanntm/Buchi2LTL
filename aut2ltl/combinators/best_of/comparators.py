"""
aut2ltl/best_of/comparators.py — the result comparators (`best_of`'s `beats` policies).

A `Comparator` answers ONE question for `best_of`: is `challenger` a better FORM of
the language than the held `incumbent` (and should unseat it)? All the results denote
the same language, so this only ever picks a better formulation — never changes what
is expressed. It is the single pluggable seam where "which form is better" is decided
— a comparison of two whole `LTLResult`s, so a policy may weigh anything (size, a
significance margin, temporals, technique, …), not just one scalar.

This module is the catalog. Each comparator is a small pure function `(incumbent,
challenger) -> bool` (or a factory returning one); add a policy by writing it here,
listing it in `__all__`, and giving it a one-liner in the package README. Keep them
free of side effects and total (defined on every pair, incl. formula-less results).
"""
from __future__ import annotations

import math
from typing import Optional, Protocol

from aut2ltl.result import LTLResult
from aut2ltl.ltl.metrics import dag_node_count


class Comparator(Protocol):
    """The behavioral contract of a `best_of` result comparator (its `beats` policy).

    INTENT. Every result `best_of` weighs denotes the SAME language — each is
    language-faithful, a different LTL *formulation* of the one language we are
    reconstructing. A comparator's entire job is to choose a **better FORM** of that
    language: smaller, better-factored, more readable. It decides whether `challenger`
    is a better form than the held `incumbent` and should unseat it. It never changes
    *what* is expressed, only *how* — so it can never make the portfolio unsound.

    A plain function `(incumbent, challenger) -> bool` conforms structurally; this
    Protocol names the role and pins the obligations:

    - **Total** — defined on every pair, including formula-less results (a NOK result
      or an unfilled accumulator). A formula-less challenger must not win.
    - **Pure** — no side effects; the verdict depends only on the two results.
    - **Tie-keeping** — return `False` when neither is clearly a better form, so
      `best_of` falls back to cited order (the first answer is the trusted incumbent).
    - **Sound by delegation** — a comparator only RANKS results `best_of` has already
      filtered to OK (faithful); it judges form, never soundness, so whatever it
      returns the winner stays faithful. It is a *preference*, not a gate.
    """

    def __call__(self, incumbent: LTLResult, challenger: LTLResult) -> bool: ...


def _size(r: LTLResult) -> Optional[int]:
    """The DAG-node count of a result's formula (what the survey/benchmark report as
    "DAG nodes"); `None` when there is no formula. Derived here, not stored on the
    result — the contract floor stays free of the metric layer."""
    return dag_node_count(r.formula) if r.formula is not None else None


def smaller(incumbent: LTLResult, challenger: LTLResult) -> bool:
    """Strict-min on DAG-node size: the challenger wins iff its size is strictly less
    than the incumbent's (a formula-less result never wins; it only seeds over a
    sizeless incumbent). Ties keep the incumbent, so order is the tiebreak."""
    ci, cc = _size(incumbent), _size(challenger)
    if cc is None:
        return False
    if ci is None:
        return True
    return cc < ci


def significantly_smaller(rel: float = 0.0, floor: int = 1) -> Comparator:
    """The *guidance* policy: the challenger wins only when it beats the incumbent's
    DAG-node size by a SIGNIFICANT margin —

        incumbent_size − challenger_size  ≥  max(floor, ceil(rel × incumbent_size))

    an absolute `floor` (so small instances, where a percentage is misleading, demand
    a real drop) OR-ed with a relative `rel` fraction (so large instances switch on a
    proportional win). `floor` dominates small incumbents, `rel` dominates large ones,
    with no size special-casing. Tune `rel`/`floor` as policy; the mechanism is fixed.
    """
    def beats(incumbent: LTLResult, challenger: LTLResult) -> bool:
        ci, cc = _size(incumbent), _size(challenger)
        if cc is None:
            return False
        if ci is None:
            return True
        return ci - cc >= max(1, floor, math.ceil(rel * ci))
    return beats


__all__ = ["Comparator", "smaller", "significantly_smaller"]
