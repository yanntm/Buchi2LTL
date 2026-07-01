# memo — the memoizing decorator

A transparent decorator that caches a child translator's result per input language.

## Setting

```
Memo :  Translator → Translator        -- child : Language → LTLResult
```

## Definition

```
Memo(child)(L) = child(L),  evaluated at most once per Language L
```

The cache (`store`) is keyed on `(operation, Language)`: the operand is `Language`
identity, the operation is `id(child)`. It is a two-level `WeakKeyDictionary[Language,
{op-id: result}]`. `Memo` is the identity on results: it returns exactly `child`'s
formula, status and technique tags, and stamps no tag of its own.

## Sharing

A `store` defaults to per-instance (each `Memo` its own), so sharing one `Memo` across
several call sites makes the wrapped child run once per language for all of them. This
is what a never-regress combo needs:

```
m = Memo(child) ;   best_of([ m, Roundtrip(m) ])
```

both arms call the same `m`, so `child` is paid once on the seed language and only the
re-presented language is genuinely re-evaluated.

Passing a **shared** `store` (from `Memo.new_store()`) to several `Memo`s pools them
into ONE compute table `(op, operand) -> result` — a BDD-style op-cache. Because the
key carries the operation, distinct operations never collide on a language: each still
answers only for itself, so a whole pipeline (decomposers, peels, a simplifier) can
share a single store without any stage shadowing another.

## Faithfulness

`Memo` is the identity on results, so it inherits `child`'s faithful-or-⊥ contract
verbatim. Its effect is purely operational (sharing), never semantic.

## Dependencies

Keyed on `(id(child), Language)` via a two-level `weakref.WeakKeyDictionary`;
otherwise only the `Translator` / `Language` types (the floor). No engine.
