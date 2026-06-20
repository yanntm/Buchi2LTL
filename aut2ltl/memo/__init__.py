"""
aut2ltl.memo — the memoizing decorator brick.

`Memo(child)` is a transparent performance decorator: a Translator that returns
exactly what `child(lang)` returns, computed at most once per `Language`. It is
the identity on results — same formula, status and technique tags — so it
inherits the faithful-or-declines contract verbatim and stamps no tag of its own.

The cache is per-instance (the flexible placement): share one `Memo` across
several call sites and the wrapped child runs once per language for all of them
— which is exactly what a never-regress combo (`best_of([m, Roundtrip(m)])`,
one shared `m = Memo(child)`) needs so the expensive child is not run twice.
See README.md.

Public entry: `Memo`.
"""

from .memo import Memo

__all__ = ["Memo"]
