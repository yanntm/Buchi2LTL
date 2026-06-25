# decompose — the ∧/∨ combine (and/or) combinator

A decorator that splits a language, labels each part with the child translator, and
recombines the part-formulas under a connective.

## Setting

```
Connective =  [spot.formula] → spot.formula        -- ∧ or ∨
Split      =  Language → [spot.twa_graph]           -- the sub-languages
decompose  :  (Split, Connective, tag) → Decorator
```

The `Split` provides the sub-automata; the `Connective` is the boolean fuse (`∧` or
`∨`). Both are parameters — `decompose` is the engine-free *operator*; the concrete
splits (strength, acceptance, scc) live in `aut2ltl/decomp/` and supply them.

## Definition

```
decompose(split, connective, tag)(child) = Λ
  where  Λ(L) =  combine(connective, tag, [ child(Lᵢ)  for Lᵢ in split(L) ])

combine(connective, tag, parts):
    if any part declined            → ⊥        -- the whole decomposition declines
    else  OK( connective([ pᵢ.formula ]) ), crediting every part, tagged `tag`
```

So a part that the child cannot label collapses the decomposition to `⊥` (the recipe
falls back), and otherwise the part-formulas are joined by `∧`/`∨`.

## Faithfulness

`decompose` is faithful **iff the split is a language (de)composition for the
connective**: for `∨`, `L = ⋃ᵢ L(Lᵢ)`; for `∧`, `L = ⋂ᵢ L(Lᵢ)`. Given that, and a
faithful-or-⊥ child, `L(connective(φᵢ)) = connective(L(φᵢ)) = L`. The obligation to
supply a genuine split rests on the concrete decomposer; `decompose` itself only fuses.

## Example

The strength decomposition: `split` cuts the automaton into its weak / terminal /
strong parts, `connective = ∨`, so `decompose(strength_split, ∨, "strength")(child)`
labels each part with `child` and disjoins — `child` declining on one part declines the
whole, and `best_of`/`first_success` then fall back.

## Dependencies

`aut2ltl.language.Language`, `aut2ltl.result.{LTLResult, fuse}` (the floor); the
sibling combinator `aut2ltl.combinators.recurse`; `aut2ltl.ltl.builders.own_simplify`
(engine-agnostic, Spot-only); and `spot` for the formula/automaton types. No engine, no
concrete decomposer.
