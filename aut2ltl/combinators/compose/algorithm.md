# compose — decorator composition (∘) and its unit (`identity`)

Function composition on the **decorator** sort, with its neutral element.

## Setting

The algebra has two sorts: translators (`X → LTLResult`) and **decorators**
`d : Translator → Translator` (a translator-to-translator map; see
`aut2ltl.translator.Decorator`). This module is the decorator sort's composition and
unit.

```
identity :  Translator → Translator
compose  :  Decorator* → Decorator
```

## Definition

```
identity(leaf)            = leaf
compose(d₁,…,dₙ)(leaf)    = d₁(d₂(… dₙ(leaf) …))      -- outermost-first
compose()                 = identity
```

A right fold: the rightmost decorator wraps the leaf first. Listing order matches the
visual nesting, so a recipe reads top-down as the term it denotes.

## Properties

`(Decorator, ∘, identity)` is a monoid: `∘` is associative and `identity` is neutral
(`compose(…) ∘ identity = compose(…)`). `identity` is the unit of *composition*, not
the `decline` terminal — `decline` is a translator (the unit of the *choice*
combinators), `identity` is a decorator (the map `Λ ↦ Λ`).

## Example

A recipe as a flat, diffable term:

```
compose(StrengthDecompose, AccDecompose, daisy_pair)(core)
        ≡  StrengthDecompose(AccDecompose(daisy_pair(core)))
```

## Faithfulness

`∘` introduces no behaviour: the composite applies the given decorators, each of which
preserves its child's faithful-or-⊥ by its own argument. `identity` is literally the
identity map.

## Dependencies

Only the `Translator` / `Decorator` types (the floor, imported under `TYPE_CHECKING`).
Pure: `functools.reduce`, no runtime engine import.
