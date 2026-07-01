"""aut2ltl/combinators/memo/memo.py — the memoizing decorator brick (`Memo`).

A transparent performance decorator: `Memo(child)` returns exactly what
`child(lang)` returns, but computes it at most once per `Language`. It is the
identity on results — same formula, same status, same technique tags — so it
inherits the Translator faithful-or-declines contract verbatim and stamps no
tag of its own.

The cache is keyed on `(operation, Language)`: the operand is the interned
`Language`, and the operation is the wrapped child's identity (`id(child)`, a
constant-time key). That op dimension lets ONE cache hold MANY operations without
collision — pass a shared `store` (`Memo.new_store()`) to several `Memo`s and they
become a single BDD-style compute table `(op, operand) -> result`, where each
operation still answers only for itself. With the default per-instance store and a
single child the op key is constant, so it degenerates to a plain per-`Language`
cache (e.g. the shared `m = Memo(child)` feeding `best_of([m, Roundtrip(m)])`).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional
from weakref import WeakKeyDictionary

if TYPE_CHECKING:
    from aut2ltl.language import Language
    from aut2ltl.result import LTLResult
    from aut2ltl.translator import Translator
    # Language -> {op-id: result}: outer weak key drops a language's whole bucket
    # when the language is collected; inner key is the operation identity.
    Store = WeakKeyDictionary[Language, Dict[int, LTLResult]]


class Memo:
    """Memoize a child Translator on the `(operation, Language)` key.

    `Memo(child)` is a Translator that delegates to `child` and caches its
    `LTLResult`. The operand key is the `Language` identity: `Language` has no
    `__eq__`/`__hash__` override and is interned (same source -> same object), so
    identity *is* the key, no separate signature needed. The operation key is
    `id(child)` — cheap and stable for the wrapper's lifetime (children are built
    once and outlive every translation, so the id is never reused underneath us).

    The cache (`store`) is a two-level `WeakKeyDictionary[Language, {op-id: result}]`:
    the outer weak key releases a `Language`'s whole bucket exactly when that
    `Language` is collected (it never pins one against the intern LRU). Pass a shared
    `store` (from `Memo.new_store()`) to several `Memo`s to make them ONE compute
    table across all their operations — a language resolved by one operation does not
    shadow another, so e.g. a memoized simplifier and a memoized decomposer coexist
    under `(L, simplify)` and `(L, decompose)`. Omit it and each `Memo` gets its own.

    Share-on-hit: a hit returns the *same* `LTLResult` object — it is a cache, not
    a consing table; it neither copies nor unifies. Safe because the combine algebra
    (`credit`/`fuse`/`best_of`) only reads a child result; the per-call accumulator a
    consumer mutates is always its own, never this one.

    Soundness is inherited verbatim: `Memo` forwards the child's result untouched, so
    it is language-faithful-or-declined iff the child is.
    """

    def __init__(self, child: "Translator", *, name: str = "memo",
                 store: "Optional[Store]" = None) -> None:
        self._child = child
        self.name = name
        self._store: "Store" = WeakKeyDictionary() if store is None else store

    @staticmethod
    def new_store() -> "Store":
        """A fresh shared store: pass it to several `Memo`s to pool them into one
        `(operation, Language)` compute table."""
        return WeakKeyDictionary()

    def __call__(self, lang: "Language") -> "LTLResult":
        bucket = self._store.get(lang)
        if bucket is None:
            bucket = {}
            self._store[lang] = bucket
        opk = id(self._child)
        hit = bucket.get(opk)
        if hit is None:
            hit = self._child(lang)
            bucket[opk] = hit
        return hit
