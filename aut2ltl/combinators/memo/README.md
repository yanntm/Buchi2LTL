# aut2ltl.memo — the memoizing decorator brick

A single decorator, `Memo`, kept in its own package so the *idea* has a home and
a README — a primitive brick beside `first_success` (choice) and `recurse`
(self-reference), not a pile of helpers.

## What it is

```
Memo(child)(lang) = child(lang)        computed at most once per lang
```

A **transparent** Translator decorator: it returns *exactly* what `child(lang)`
returns — same formula, same status, same `technique` tags — but caches the
result, so a second call with the same `Language` skips the child entirely. It
is the identity on results; it stamps no tag of its own (like `first_success`,
the wrapper's `name` is its identity, not a technique).

## Why a brick

The cascade and GAP are the expensive part of a translation. A combo like the
never-regress round trip wants to run one child on the *same* language at two
sites:

```
best_of([ m, Roundtrip(m) ])        with a single   m = Memo(child)
```

Without a memo this runs `child(L)` twice (incumbent + seed). `Memo` makes the
second a cache hit. The cache lives **on the instance**, so *sharing the cache is
sharing the instance* — placement-flexible, and the recipe controls reuse by
deciding which sites point at the same `Memo`.

## How it keys, and why it releases

The cache is keyed on `(operation, Language)`. `Language` has no `__eq__` /
`__hash__` override (it keys by identity) and is **interned** (same source ->
same object), so identity is the operand key — no separate signature. The
operation key is `id(child)`, a constant-time value that is stable for the
wrapper's lifetime (children are built once and outlive every translation, so the
id is never reused underneath us).

That operation dimension is what lets **one** cache hold **many** operations
without collision. Pass a shared `store` (from `Memo.new_store()`) to several
`Memo`s and they become a single BDD-style compute table `(op, operand) -> result`
— a language resolved by one operation never shadows another, so e.g. a memoized
simplifier and a memoized decomposer coexist under `(L, simplify)` and
`(L, decompose)`. Omit `store` and each `Memo` gets its own, keyed on its single
op — which degenerates to a plain per-`Language` cache (the shared
`m = Memo(child)` feeding `best_of([m, Roundtrip(m)])` above). Without the op key,
sharing one store across stages would make the first stage to resolve a language
an undisplaceable "king" that answers for every other stage.

The memo follows the house `.get` / insert-on-miss shape (`bls` `reach_memo` /
`helper_memo`, `ltl.builders._simp_memo`, `simplify._node_memo`), with one
difference forced by lifetime: those are *per-build* memos that die with their
holder, naturally bounded. A `Memo` instance is **long-lived** — it outlives a
single translation, across many inputs — so a plain dict would grow without
bound. The store is therefore a two-level `weakref.WeakKeyDictionary[Language,
{op-id: result}]`: the outer weak key releases a `Language`'s whole bucket (all
its operations) exactly when that `Language` is collected, and it never pins one
alive against the intern LRU in `language.py`.

## Soundness

Inherited verbatim. `Memo` forwards the child's result untouched — it is a
cache, not a consing table, so it neither copies nor unifies — therefore it is
language-faithful-or-declined iff the child is. Share-on-hit (returning the same
`LTLResult` object) is safe because the combine algebra (`credit` / `fuse` /
`best_of`) only *reads* a child result; the per-call accumulator a consumer
mutates is always its own.
