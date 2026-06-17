"""
aut2ltl/contract.py — the contract floor: the behavioral Translator signatures.

kr has become a PORTFOLIO: a given automaton is reconstructed by whichever
method wins at each node of the decompose-and-recombine dispatch — the
buchi2ltl gate, an AND/OR strength/acceptance split, or one of the leaf
acceptance-dispatch forms (acc / weak / buchi / cobuchi / the Muller-DNF
cascade `bls`). The bare `spot.formula` return hid which method fired, so a
translator now returns a `Result` (`aut2ltl.result`), carrying the formula plus
the SET of methods that contributed.

`Result.technique` is a set (deduped) accumulated down the dispatch tree:
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

This module is the contract FLOOR both engines depend on: the behavioral
signatures `Translator` (automaton in) and `CascadeTranslator` (decomposed
cascade in). The result data type and its lifecycle (the closed `Status`, the
`credit`/`fuse` and `first` algebras) live in `aut2ltl/result.py` — see
`aut2ltl/result.md` for the model. A result is OK (a language-faithful formula),
DECLINED ("not my method, try another"), or NOT_LTL (a positive impossibility
verdict — the language is not LTL-definable, so no method can succeed): a
consumer keeps trying on DECLINED but stops on NOT_LTL.
"""
from __future__ import annotations

from typing import Protocol, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:
    from aut2ltl.language import Language
    from aut2ltl.result import Result


@runtime_checkable
class Translator(Protocol):
    """The behavioral contract: translate a `Language` to LTL.

    A Translator is a callable `Language -> Result`. The input is a `Language`
    (the floor handle over language-equivalent automaton representations —
    `aut2ltl.language`), not a raw automaton: each translator pulls the
    representation it wants (`tgba` / `det_parity_sbacc` / `det_generic`
    / `det_generic_minimal`). The kr endpoint `aut2cas.reconstruct` realizes this;
    the portfolio combinators (Gate / Decompose / SlDriven / Portfolio) are
    themselves Translators over Translators.

    Contract invariant (NOT type-checkable, the load-bearing rule): the returned
    `Result` is either language-faithful (`status` OK, `.formula` ≡ L(lang)) or a
    NOK (DECLINED / NOT_LTL) — NEVER a wrong formula. That single rule is what
    makes composition sound.
    """

    def __call__(self, lang: "Language") -> "Result": ...


@runtime_checkable
class CascadeTranslator(Protocol):
    """The cascade-level peer of `Translator`: translate a Krohn-Rhodes Cascade
    to LTL.

    Same `Result` and the same load-bearing invariant — the result is
    language-faithful (OK) or a NOK, never wrong — but the input is an already
    decomposed cascade (a `CascadeHolder` wrapping it) instead of a raw automaton.

    Realized as an OO family: each construction is a *member* — a small class
    (singleton instance) with a fixed `name` (its technique identity, e.g.
    'acc' / 'buchi' / 'cobuchi' / 'weak' / 'bls') and a `__call__` that is
    self-gating (it inspects the cascade and either builds its faithful form or
    DECLINES). The member stamps its own `name` into the `Result`'s technique,
    so composites (`first_success`) need no out-of-band tagging. `decompose_aut`
    is the adapter that lifts a member up to a `Translator` (twa -> Cascade ->
    result).

    The `CascadeHolder` annotation is a bare forward-ref string (like
    `Translator`'s `spot.twa_graph`) so this floor module stays import-free of the
    engines. The holder wraps the pure `Cascade` with that build's caches/counters
    (kr/cascade/holder.py); members read cascade attributes off it transparently.
    """

    name: str

    def __call__(self, casc: "CascadeHolder") -> "Result": ...
