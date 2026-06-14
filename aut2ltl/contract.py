"""
aut2ltl/contract.py — the contract floor: the portfolio result struct.

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

This module is the contract FLOOR both engines depend on: the data signature
`LTLFormulaResult` and the behavioral signatures `Translator` (automaton in) and
`CascadeTranslator` (decomposed cascade in). The key reification is an explicit
`status` (OK / DECLINED) — "not me" is no longer smuggled as the `UNSUPPORTED`
string inside `.formula`. `status` plus the dataclass being the single extension
point (add a `cost`/size field when a pick-smaller combinator needs an ordering)
is what lets the combinators compose soundly.
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
class LTLFormulaResult:
    """A reconstructed formula DAG, the set of methods that built it, and an
    explicit status. On DECLINE `.formula` is None and `.status` is DECLINED
    (use `LTLFormulaResult.decline(...)`); never a sentinel string in `.formula`."""
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
    def decline(cls, technique: Optional[Set[str]] = None) -> "LTLFormulaResult":
        """The "not me" result: no formula, DECLINED status."""
        return cls(formula=None, technique=technique or set(), status=DECLINED)

    def technique_str(self) -> str:
        """Stable '+'-joined rendering (sorted) for logs/surveys."""
        return "+".join(sorted(self.technique)) if self.technique else "-"


@runtime_checkable
class Translator(Protocol):
    """The behavioral contract: translate a HOA automaton to LTL.

    A Translator is a callable `twa -> LTLFormulaResult`. Current realizations are
    plain module functions (`reconstruct_decomposed`, buchi2ltl's
    `reconstruct_ltl`, the acceptance-dispatch leaves); this Protocol documents
    the shared signature, and the portfolio combinators (Gate / Decompose /
    SlDriven / Portfolio) are themselves Translators over Translators.

    Contract invariant (NOT type-checkable, the load-bearing rule): the returned
    LTLFormulaResult is either language-faithful (`status` OK, `.formula` ≡ L(twa)) or
    DECLINED — NEVER a wrong formula. That single rule is what makes composition
    sound.
    """

    def __call__(self, twa: "spot.twa_graph") -> "LTLFormulaResult": ...


@runtime_checkable
class CascadeTranslator(Protocol):
    """The cascade-level peer of `Translator`: translate a Krohn-Rhodes Cascade
    to LTL.

    Same `LTLFormulaResult` and the same load-bearing invariant — the result is
    language-faithful (OK) or DECLINED, never wrong — but the input is an already
    decomposed `Cascade` instead of a raw automaton.

    Realized as an OO family: each construction is a *member* — a small class
    (singleton instance) with a fixed `name` (its technique identity, e.g.
    'acc' / 'buchi' / 'cobuchi' / 'weak' / 'bls') and a `__call__` that is
    self-gating (it inspects the cascade and either builds its faithful form or
    DECLINES). The member stamps its own `name` into the LTLFormulaResult's technique,
    so composites (`first_success`) need no out-of-band tagging. `decompose_aut`
    is the adapter that lifts a member up to a `Translator` (twa -> Cascade ->
    result).

    The `Cascade` annotation is a bare forward-ref string (like `Translator`'s
    `spot.twa_graph`) so this floor module stays import-free of the engines.
    """

    name: str

    def __call__(self, casc: "Cascade") -> "LTLFormulaResult": ...
