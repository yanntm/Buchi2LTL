"""aut2ltl/memo/memo.py — the memoizing decorator brick (`Memo`).

A transparent performance decorator: `Memo(child)` returns exactly what
`child(lang)` returns, but computes it at most once per `Language`. It is the
identity on results — same formula, same status, same technique tags — so it
inherits the Translator faithful-or-declines contract verbatim and stamps no
tag of its own.

The cache lives on the instance (per-`Memo`, the flexible placement): sharing
one `Memo` across several call sites — e.g. `best_of([m, Roundtrip(m)])` with a
single `m = Memo(child)` — computes the wrapped child once per language and
hands both sites the shared result. That is the whole point of the brick.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

if TYPE_CHECKING:
    from aut2ltl.language import Language
    from aut2ltl.result import LTLResult
    from aut2ltl.translator import Translator


class Memo:
    """Memoize a child Translator on the (interned) `Language` identity.

    `Memo(child)` is a Translator that delegates to `child` and caches its
    `LTLResult` per `Language`. `Language` has no `__eq__` / `__hash__` override,
    so it keys by identity, and it is interned (same source -> same object) — so
    identity *is* the cache key, no separate signature needed.

    The memo follows the house `.get` / insert-on-miss shape (see
    `bls` `reach_memo` / `helper_memo`, `ltl.builders._simp_memo`), with one
    difference dictated by lifetime: those memos are *per-build* and die with
    their holder, whereas a `Memo` instance is long-lived (it outlives a single
    translation, across many inputs), so a plain dict would grow without bound.
    The cache is therefore a `WeakKeyDictionary`: an entry is released exactly
    when its `Language` is (it never pins one alive against the intern LRU).

    Share-on-hit: a hit returns the *same* `LTLResult` object — it is a cache,
    not a consing table; it neither copies nor unifies. Safe because the combine
    algebra (`credit` / `fuse` / `best_of`) only reads a child result; the
    per-call accumulator a consumer mutates is always its own, never this one.

    Soundness is inherited verbatim: `Memo` forwards the child's result
    untouched, so it is language-faithful-or-declined iff the child is.
    """

    def __init__(self, child: "Translator", *, name: str = "memo") -> None:
        self._child = child
        self.name = name
        self._cache: "WeakKeyDictionary[Language, LTLResult]" = WeakKeyDictionary()

    def __call__(self, lang: "Language") -> "LTLResult":
        hit = self._cache.get(lang)
        if hit is None:
            hit = self._child(lang)
            self._cache[lang] = hit
        return hit
