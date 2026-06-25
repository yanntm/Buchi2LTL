"""
aut2ltl/compose.py — decorator composition (`∘`) and its unit (`identity`).

The combinator algebra over language-manipulators has two sorts: translators
(`Language -> LTLResult`) and decorators (`Translator -> Translator`, see
`aut2ltl.translator.Decorator`). `first_success` / `best_of` (choice) and `recurse`
(fixpoint) cover the translator sort; this module is the **decorator** sort's
composition `∘` and its unit `identity`.

It exists so a recipe can be written as a flat, diffable *term* — `compose(Strength,
Acc, daisy_pair)(core)` instead of the inside-out `Strength(Acc(daisy_pair(core)))`
— rather than as nested constructor calls. No DSL, no operators: two small functions.
"""
from __future__ import annotations

from functools import reduce
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aut2ltl.translator import Translator, Decorator


def identity(leaf: "Translator") -> "Translator":
    """The decorator-algebra unit (`id`): return the translator unchanged.

    The neutral element of `compose` (`compose(...) ∘ identity == compose(...)`). It
    is NOT the `decline` terminal — `decline` is a translator (a leaf that always
    declines, the unit of the *choice* combinators); `identity` is a *decorator* (a
    map `Λ ↦ Λ`, the unit of composition). Its first use is the `best_of` pairing
    `best_of([identity(Λ), inv(Λ)])` — "take inv's form only if it wins"."""
    return leaf


def compose(*decorators: "Decorator") -> "Decorator":
    """Compose decorators outermost-first: `compose(f, g, h)(leaf) == f(g(h(leaf)))`.

    The listing order matches the visual nesting (`f` is the outermost wrap), so a
    recipe reads top-down as the term it denotes. `compose()` with no arguments is
    `identity`. A right fold over the arguments, applying the rightmost decorator to
    the leaf first."""
    def composed(leaf: "Translator") -> "Translator":
        return reduce(lambda acc, dec: dec(acc), reversed(decorators), leaf)
    return composed
