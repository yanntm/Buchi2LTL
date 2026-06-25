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

The cache is a per-instance table keyed on `Language` identity (a
`WeakKeyDictionary`). `Memo` is the identity on results: it returns exactly `child`'s
formula, status and technique tags, and stamps no tag of its own.

## Sharing

Because the cache is per-instance, sharing one `Memo` across several call sites makes
the wrapped child run once per language for all of them. This is what a never-regress
combo needs:

```
m = Memo(child) ;   best_of([ m, Roundtrip(m) ])
```

both arms call the same `m`, so `child` is paid once on the seed language and only the
re-presented language is genuinely re-evaluated.

## Faithfulness

`Memo` is the identity on results, so it inherits `child`'s faithful-or-⊥ contract
verbatim. Its effect is purely operational (sharing), never semantic.

## Dependencies

Keyed on `Language` identity via `weakref.WeakKeyDictionary`; otherwise only the
`Translator` / `Language` types (the floor). No engine.
