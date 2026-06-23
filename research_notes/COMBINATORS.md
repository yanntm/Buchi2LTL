# The combinator algebra

`aut2ltl` is a portfolio: translators (`Language -> LTLResult`) composed by a few
combinators. Those combinators form a small **(almost-)algebra over language-
manipulators** — naming its operations is what lets a recipe be read as a *term*. This
note is the conceptual lens (and the law table); it is not a spec to enforce, and there
is deliberately **no DSL, no operator overloading, no term-as-data/AST, and no
meta-level reflection** on composition — just free named functions.

## Carrier and the load-bearing invariant

The carrier is **translators** — each a way to manipulate a language into an LTL form,
or to decline. Every translator carries the invariant **faithful-or-⊥**: its
`LTLResult` is language-equivalent (OK) or a NOK (`DECLINED` / `NOT_LTL`), never a wrong
formula (`aut2ltl/translator.py`, `aut2ltl/result.py`).

There are two **sorts**: translators, and **decorators** (`Translator -> Translator`,
`aut2ltl/translator.py::Decorator`) — `StrengthDecompose`, `AccDecompose`, `Invariant`,
`daisy_pair`, a `recurse` step.

## Operations

| op | symbol | code | sort | neutral |
|---|---|---|---|---|
| choice-by-order | `⊕` | `first_success` (`aut2ltl/first_success.py`) | translators → translator | `decline` |
| choice-by-form | `⊞` | `best_of` (`aut2ltl/best_of/`) | translators → translator | `decline` |
| composition | `∘` | `compose` (`aut2ltl/compose.py`) | decorators → decorator | `identity` |
| fixpoint | `fix` | `recurse` (`aut2ltl/recurse/`) | decorator → translator | — |
| combine | `∧`/`∨` | `decompose`/`combine` (`aut2ltl/decomp/decompose.py`, = `fuse` + connective) | results → result | (`OK`-seed) |

**Neutrals are two distinct gadgets.** `decline` is the **terminal** (a translator: the
leaf that always declines, the unit of the choice operations). `identity` is the
**identity** (a decorator `Λ ↦ Λ`, the unit of `∘`). A terminal is an element; an
identity is a map — do not conflate them.

## The one law: soundness is closed under every operation

Every operation **preserves faithful-or-⊥**. So the invariant is closed under the whole
vocabulary, which means: **any term you can write — any recipe — is sound by
construction.** This is why you never inspect a composite to trust it; reason locally
(each operation's contract) and closure does the rest. (We rely on this constantly:
`inv` idempotence let us stack `Invariant` freely; `⊕` associativity flattens ladders;
the survey cannot go non-equivalent however we wire.)

## The negative laws (stated loudly, on purpose)

The equational laws are **partial** — that is the "almost". Do not assume what does not
hold:

- `⊕` (`first_success`) is **not commutative** — cited order is priority.
- `⊞` (`best_of`) under a significance margin is **not associative** — the threshold is
  relative to the running incumbent (it *is* a semilattice under strict-min `smaller`).
- `fix` (`recurse`) is **not** a monoid — it is a least fixpoint, and each step owes a
  well-founded-descent (termination) obligation that stays explicit.

## Recipes are terms; two recurse bodies

A recipe is a term in this vocabulary, e.g. the default:

```
core        = PartScc ⊕ Bls
daisy_pair  = fix( λℓ. Daisy(ℓ) ⊕ Daisy2(ℓ) ⊕ core )
best_daisy2 = Simplify ∘ Strength ∘ Acc ∘ daisy_pair        (Simplify carries its level arg outside compose)
```

Note the two shapes of `recurse` body: **daisy**'s is a *choice* (`⊕`: try a peel, else
floor — one continuation); **decomp**'s is a *combine* (`∧/∨`: split into all pieces,
recurse each, fold) — the *same* `fix`, a different body operation.

## Pointers

`aut2ltl/portfolio/README.md` (how recipes wire), `aut2ltl/recurse/README.md` and
`aut2ltl/best_of/README.md` (the bricks and their contracts), `aut2ltl/decomp/decompose.py`
(the shared decomposition combinator).
