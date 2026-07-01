"""
aut2ltl.combinators.memo — the memoizing decorator brick.

`Memo(child)` is a transparent performance decorator: a Translator that returns
exactly what `child(lang)` returns, computed at most once per `Language`. It is
the identity on results — same formula, status and technique tags — so it
inherits the faithful-or-declines contract verbatim and stamps no tag of its own.

The cache is keyed on `(operation, Language)` (operation = `id(child)`). By
default each `Memo` owns its store, so sharing one `Memo` across several call
sites runs the wrapped child once per language for all of them — exactly what a
never-regress combo (`best_of([m, Roundtrip(m)])`, one shared `m = Memo(child)`)
needs so the expensive child is not run twice. Pass a shared `store`
(`Memo.new_store()`) to several `Memo`s to pool them into ONE BDD-style compute
table where distinct operations never shadow one another. See README.md.

Public entry: `Memo`.
"""

from .memo import Memo

__all__ = ["Memo"]
