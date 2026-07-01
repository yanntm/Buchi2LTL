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
  where  Λ(L) =  revalidate( combine(connective, tag, [ child(Lᵢ)  for Lᵢ in split(L) ]), L )

combine(connective, tag, parts):
    if any part declined            → ⊥        -- the whole decomposition declines
    else  OK( connective([ pᵢ.formula ]) ), crediting every part, tagged `tag`
```

So a part that the child cannot label collapses the decomposition to `⊥` (the recipe
falls back), and otherwise the part-formulas are joined by `∧`/`∨`.

## The NOT_LTL crossing (revalidate-or-degrade)

A part's `NOT_LTL` is a verdict about the **part's** language, and non-LTL-ness
survives *neither* connective: a non-LTL part intersected or unioned with another can
yield an LTL whole (the counting can be erased by the other part). So a `NOT_LTL`
crossing the combine must not be trusted — it is **revalidated against `L` itself**,
queried through the parts (`aut2ltl.verifier.revalidated_by_parts`): faithfulness
means membership of any word in `L` IS the connective of its memberships in the
parts, so the replay runs part-sized queries only — no product or determinization of
`L` is ever built (the empty fold identifies the connective: `∧([]) = tt`).

- **replays** — the family toggles on `L` directly, so the verdict is valid *here*,
  minimality- and composition-independent: keep the absorbing `NOT_LTL` (now
  certified at this level).
- **does not replay** (or no complete family) — degrade to a **non-absorbing
  decline** carrying a `PROBABLY_NOT_LTL` diagnosis: no verdict is asserted, the
  recipe falls back, and another arm (e.g. the gate on `L` itself) may still certify
  or answer.

This is the enforcement of the lift rule in
`bls/definability/witness/algorithm.md` (Lifting): a certificate is only ever
asserted against the language it was replayed on.

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
