"""deep_nobls_memo recipe — `deep_nobls` with EVERY element on ONE shared `Memo` store,
a BDD-style operation cache keyed on `(operation, Language)`.

Same assembly as `deep_nobls` (cakedsdet seed, then a bottom-up `deep_roundtrip`
re-presenting every DAG node via the no-bls decomposition), with one change: a single
`store = Memo.new_store()` is threaded through the whole recipe and every operation is
wrapped on it — the seed, each no-bls primitive (`Daisy`/`Daisy2`/`DaisystarDet`/
`Daisystar`/`PartScc`), each decomp stage, the daisy fixpoint, the whole, the arm's
simplifier, and the final simplifier. The store is one compute table keyed on
`(id(child), Language)`: the operand is the interned `Language` (BDD/HOA identity), the
operation is the wrapped instance.

`id`-keying is the safe, constant-time choice, and it is what lets ONE store hold every
operation without collision: a language resolved by one operation never shadows another
(a language-only key would make the first stage to touch a language an undisplaceable
"king", and the simplifier could not be memoized without being shadowed by a raw stage's
entry). Each distinct instance is its own sub-recipe — the two `Invariant` stages, and
the seed's vs the arm's peels, do NOT share (different engines, deliberately).

Sound because every operation is a pure function of its language (faithful-or-⊥): a
cached `op(L)` is exactly what `op` recomputes for `L`, never another op's answer — so
output is identical to `deep_nobls`. The win is operational: each `(operation, language)`
pair is computed ONCE, across the whole pipeline and every `deep_roundtrip` node (the
store is a long-lived `WeakKeyDictionary`, releasing a language's whole bucket when the
language is collected). `Memo` stamps no technique tag, so the credited stack is
unchanged from `deep_nobls`.

Motivation (kinska `counting_buchi_1ap_18`, `tests/probes/gate_count.py`): the soundness
gates fire 1271× on only 78 distinct (input, candidate) pairs — 94% exact recomputes,
one suffix re-validated 240× — because the büchi-tower suffixes are re-peeled on every
descent path. The gates are cheap (~17ms); the redundancy is the surrounding peel work
(and the expensive `hi`/r3 simplifier). The shared op cache collapses it to DAG-size
complexity.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict, Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.combinators.best_of import best_of
from aut2ltl.combinators.compose import compose
from aut2ltl.combinators.first_success import first_success
from aut2ltl.combinators.memo import Memo
from aut2ltl.ltl_rewriter import identity, relabel, as_translator
from aut2ltl.roundtrip_deep import deep_roundtrip
from aut2ltl.simplify_ltl import Simplify
from aut2ltl.daisy import Daisy
from aut2ltl.daisy2 import Daisy2
from aut2ltl.daisystar import Daisystar
from aut2ltl.daisystardet import DaisystarDet
from aut2ltl.partscc import PartScc
from aut2ltl.decomp.inv import Invariant
from aut2ltl.decomp.acceptance import AccDecompose
from aut2ltl.decomp.scc import SccDecompose
from aut2ltl.decomp.strength import StrengthDecompose
from .cakedsdet import cakedsdet

if TYPE_CHECKING:
    from aut2ltl.language import Language
    from aut2ltl.result import LTLResult
    from aut2ltl.combinators.memo.memo import Store

Decorator = Callable[[Translator], Translator]


def _nobls_memo(store: "Store") -> Translator:
    """The `nobls` assembly inlined, EVERY operation wrapped on the shared `store`
    (keyed on `(operation, Language)`): each peel primitive, the floor, the decomp
    pipeline (`Invariant ∘ Strength ∘ Scc ∘ Invariant ∘ Acc`), the daisy fixpoint, the
    whole, and the final `hi` simplifier. The daisy recursion's leaf is the memoized
    daisy fixpoint, so a shared suffix reached again is a cache hit, not a re-peel;
    floors on `PartScc()`. `recurse` is untouched — the knot is tied by hand so the memo
    can sit in it."""
    def m(child: Translator) -> Translator:
        return Memo(child, store=store)

    def md(decorator: Decorator) -> Decorator:
        return lambda child: m(decorator(child))

    holder: Dict[str, Translator] = {}

    def daisy_leaf(lang: "Language") -> "LTLResult":
        return holder["daisy"](lang)

    daisy_fix = Invariant(first_success(
        [m(Daisy(daisy_leaf)), m(Daisy2(daisy_leaf)), m(DaisystarDet(daisy_leaf)),
         m(Daisystar(daisy_leaf)), m(PartScc())],
        name="daisy_trio_det"))
    holder["daisy"] = m(daisy_fix)                       # the memoized recursion target

    pipeline = compose(md(Invariant), md(StrengthDecompose), md(SccDecompose),
                       md(Invariant), md(AccDecompose))(holder["daisy"])
    whole = m(pipeline)
    return m(Simplify(whole, "hi"))                      # the arm simplifier is memoized too


def deep_nobls_memo(options: Optional[Options] = None) -> Translator:
    """`deep_nobls` with EVERY element on one shared `Memo` compute table (BDD-style,
    keyed on `(operation, Language)`): the `cakedsdet` seed, the memoized no-bls
    return-labeler, and the final `hi` simplifier all share `store`. `cakedsdet` seeds a
    formula, `deep_roundtrip` re-presents every DAG node bottom-up via the memoized arm,
    kept per node only when not larger (`best_of([identity, relabel])`), then one final
    simplifier over the whole."""
    store = Memo.new_store()                             # the single compute table for the recipe

    def m(child: Translator) -> Translator:
        return Memo(child, store=store)

    seed = m(cakedsdet(options))
    represent = best_of([identity, relabel(_nobls_memo(store))], name="deep_nobls_arm")
    rewriter = deep_roundtrip(represent)
    return m(Simplify(as_translator(seed, rewriter), "hi"))


__all__ = ["deep_nobls_memo"]
