"""
kr/recon_result.py — the portfolio result struct.

kr has become a PORTFOLIO: a given automaton is reconstructed by whichever
method wins at each node of the decompose-and-recombine dispatch — the
buchi2ltl gate, an AND/OR strength/acceptance split, or one of the leaf
acceptance-dispatch forms (acc / weak / buchi / cobuchi / the Muller-DNF
cascade `bls`). The bare `spot.formula` return hid which method fired, so the
top-level entry now returns this struct, carrying the formula plus the SET of
methods that contributed.

`.technique` is a set (deduped) accumulated down the dispatch tree:
  * 'and<n>' / 'or<n>'           — a boolean split into n pieces occurred at some
                                   node (n = number of conjuncts / disjuncts);
                                   subsumes the old `split_report` side channel;
  * 'sl' / 't2' / 'f2'           — the buchi2ltl gate produced a node (its own
                                   technique tokens, split on '+');
  * 'acc' / 'weak' / 'buchi' /
    'cobuchi' / 'bls'            — the leaf acceptance-dispatch method
                                   (`bls` = the general Muller-DNF cascade);
  * 'base'                       — a custom (non-default) reconstruct callable
                                   produced a leaf (probes/tests).

MT-safe by construction: the accumulator is a per-call local threaded by
reference through the dispatch, never a module-level/global recorder.

CONTRACT (P-ARCH step 1, 2026-06-14). This module is the contract FLOOR both
engines depend on: the data signature `ReconResult` and the behavioral
signature `Translator`. The key reification is an explicit `status` (OK /
DECLINED) — "not me" is no longer smuggled as the `UNSUPPORTED` string inside
`.formula`. `status` plus the dataclass being the single extension point
(add a `cost`/size field when a pick-smaller combinator needs an ordering) is
what lets the portfolio combinators compose soundly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, Set, runtime_checkable

# status values
OK = "OK"
DECLINED = "DECLINED"

# Legacy decline sentinel. The engines (buchi2ltl, sl) still use this string
# INTERNALLY to propagate "this state has no exact label" through their
# backward-labeling recursion; that is an engine detail, not the contract. At
# the contract boundary, decline is `status == DECLINED`. Recognized here only
# transitionally, so a consumer can switch to `.declined` before every producer
# sets `status` explicitly. TODO (P-ARCH): drop once all producers are migrated.
_LEGACY_UNSUPPORTED = "UNSUPPORTED"


@dataclass
class ReconResult:
    """A reconstructed formula DAG, the set of methods that built it, and an
    explicit status. On DECLINE `.formula` is None and `.status` is DECLINED
    (use `ReconResult.decline(...)`); never a sentinel string in `.formula`."""
    formula: Optional["spot.formula"]
    technique: Set[str] = field(default_factory=set)
    status: str = OK

    @property
    def declined(self) -> bool:
        """True iff this is a "not me" result. Consumers branch on this."""
        if self.status == DECLINED:
            return True
        # Transitional: some producers still smuggle the UNSUPPORTED string in
        # `.formula` instead of setting status. See `_LEGACY_UNSUPPORTED`.
        return isinstance(self.formula, str) and _LEGACY_UNSUPPORTED in self.formula

    @property
    def ok(self) -> bool:
        """True iff this carries a real (language-faithful) formula."""
        return not self.declined

    @classmethod
    def decline(cls, technique: Optional[Set[str]] = None) -> "ReconResult":
        """The "not me" result: no formula, DECLINED status."""
        return cls(formula=None, technique=technique or set(), status=DECLINED)

    def technique_str(self) -> str:
        """Stable '+'-joined rendering (sorted) for logs/surveys."""
        return "+".join(sorted(self.technique)) if self.technique else "-"


@runtime_checkable
class Translator(Protocol):
    """The behavioral contract: translate a HOA automaton to LTL.

    A Translator is a callable `twa -> ReconResult`. Current realizations are
    plain module functions (`reconstruct_decomposed`, buchi2ltl's
    `reconstruct_ltl`, the acceptance-dispatch leaves); this Protocol documents
    the shared signature, and the portfolio combinators (Gate / Decompose /
    SlDriven / Portfolio) are themselves Translators over Translators.

    Contract invariant (NOT type-checkable, the load-bearing rule): the returned
    ReconResult is either language-faithful (`status` OK, `.formula` ≡ L(twa)) or
    DECLINED — NEVER a wrong formula. That single rule is what makes composition
    sound.
    """

    def __call__(self, twa: "spot.twa_graph") -> "ReconResult": ...
