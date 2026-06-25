# first_success — the choice combinator (⊕)

A composite translator that returns the result of the first stage that does not
decline.

## Setting

```
stages   t₁ … tₙ  :  X → LTLResult     -- generic in the input X
⊕[t₁…tₙ] :  X → LTLResult
```

`LTLResult` is three-valued: `OK(φ)` (a language-faithful formula), `DECLINED` (⊥,
"not my case"), `NOT_LTL` (a definability verdict).

## Definition

```
⊕[t₁…tₙ](x) =  tᵢ(x)   for the least i with ¬declined(tᵢ(x))
               ⊥        if every stage declines
```

Only `DECLINED` continues the walk. Both `OK` and `NOT_LTL` stop it: a verdict means
*no* stage can produce a faithful formula (a later stage would re-derive the same
verdict), so returning it preserves the reason. The winning result is returned
unchanged — the composite stamps no technique of its own; its `name` is its identity.

## Properties

Associative, with the always-declining leaf as unit. A composite is itself a
translator, so `⊕` nests.

## Example

The acceptance-dispatch chain `acc ⊕ weak ⊕ buchi ⊕ cobuchi ⊕ bls`: each leaf
self-gates, declining off the fragment it handles; the first that applies answers, and
its result flows out untouched.

## Faithfulness

The output is some `tᵢ(x)` verbatim. Each stage is faithful-or-⊥ by contract, hence so
is `⊕`.

## Dependencies

`aut2ltl.result.LTLResult` only — the contract floor. Generic in the stage input type,
so it composes `Translator` (Language in) and cascade stages alike. No engine.
