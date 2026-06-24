# The ltl_rewriter contract

A **Rewriter** re-presents an LTL result as another: `LTLResult → LTLResult`. It is
the formula-space peer of `Translator` (`Language → LTLResult`) — same codomain and
the same composition algebra, but its input is an *already-held formula* (carrying the
provenance accumulated so far) rather than an automaton. The semantic re-derivations
(cut / roundtrip / multicut) and the syntactic simplifications are all Rewriters, and
they compose through the existing `LTLResult` monoids.

## Setting

```
Translator  =  Language  → LTLResult          -- automaton → formula  (the seed / leaf)
Rewriter    =  LTLResult → LTLResult          -- formula  → formula   (re-presentation)
```

A Rewriter receives an OK result carrying a formula and returns either a faithful
re-presentation or a decline. **Faithful** means ω-equivalent to the input:

```
R(r) = Some r'   ⇒   r'.formula ≡ r.formula
```

That single invariant is the whole soundness obligation — no transition structure, and
no `NOT_LTL` (the input is already a formula, hence LTL-definable). Decline (`⊥`) is
kept: it closes composition under `first_of` / `best_of`, exactly as for `Translator`.

## identity

```
identity(r) = r
```

The unit Rewriter: faithful, never declines. It is the **never-regress floor** —
`best_of(identity, R)` can only improve on `r`, never regress, never decline.

## The boundary adapters

The two — and only two — places `Language` / `Translator` meet the Rewriter world:

```
relabel(Λ) : Rewriter
relabel(Λ)(r) =  Λ( lang(r.formula) )         -- crediting r; ⊥ if Λ declines / untranslatable
```

Lift a `Translator` *into* a Rewriter: take the formula out of `r`, re-describe its
language, re-label with `Λ`. This is the semantic re-derivation as a rewrite, and the
one place a Rewriter decline originates.

```
as_translator(seed, R) : Translator
as_translator(seed, R)(L) =  let r = seed(L) in  r.nok ? r : R(r)
```

Masquerade a Rewriter *back as* a `Translator` for the portfolio: the `seed`
(automaton → formula) is the lone automaton step and the only place `NOT_LTL` arises;
everything after is Rewriter.

## Composition

A Rewriter shares `Translator`'s codomain, so it reuses the existing `LTLResult`
algebra unchanged:

- `credit` / `fuse` — a child re-presentation's techniques fold into the parent
  result, so traceability is preserved across the chain;
- `first_of` / `best_of` — already generic in the input type (`X → LTLResult`), so the
  same combinators drive both Translators (`X = Language`) and Rewriters
  (`X = LTLResult`); a decline falls through, the comparator keeps the smaller.

## Soundness

Every Rewriter preserves the ω-language (`R(r) ≡ r`, or `⊥`): `identity` and the LTL
simplification pass do so syntactically; `relabel(Λ)` because `Λ` is faithful and
`lang` preserves the language. Faithful Rewriters compose to faithful Rewriters, and
`as_translator` lifts a faithful Rewriter to a faithful-or-NOK Translator. Soundness
therefore lives in this one contract plus the two boundary adapters.
