# aut2ltl.combinators — the Translator-algebra bricks

Six general-purpose combinators for building translators out of translators. Each
depends on nothing but the **contract floor** (`aut2ltl.translator.Translator` /
`aut2ltl.result.LTLResult`) — and, where a size objective is needed (`best_of`), the
engine-agnostic `aut2ltl.ltl` metrics, itself dependency-free but for Spot. **None
depends on a concrete contract realization** (any engine). Each carries a formal
`algorithm.md`.

## Setting

A **translator** is a map `t : X → LTLResult` (with `X = Language` at the top level,
or a cascade input deeper down). `LTLResult` is three-valued:

```
OK(φ)      a formula            — language-faithful:  L(φ) = L(x)
DECLINED   ⊥ (no opinion)       — "not my case"
NOT_LTL    a definability verdict — no LTL formula exists
```

The **load-bearing invariant** is *faithful-or-⊥*: a translator either returns a
language-faithful formula or declines (or reports `NOT_LTL`); it never returns a wrong
formula. A **decorator** is a map `d : Translator → Translator` (a second sort).

**Soundness is closed under every combinator below**, so any term built from them is
sound by construction — this is what lets recipes be written freely.

## The bricks

| brick | sort | symbol | one-line | spec |
|---|---|---|---|---|
| `first_success` | choice | ⊕ | first non-declined stage | [first_success/algorithm.md](first_success/algorithm.md) |
| `best_of` | choice-by-size | ⊞ | trusted incumbent, beaten only by a comparator | [best_of/algorithm.md](best_of/algorithm.md) |
| `compose` | decorator monoid | ∘ | `d₁∘…∘dₙ`, unit `identity` | [compose/algorithm.md](compose/algorithm.md) |
| `recurse` | fixpoint | fix | `leaf = step(leaf)` | [recurse/algorithm.md](recurse/algorithm.md) |
| `memo` | decorator | — | transparent per-`Language` sharing | [memo/algorithm.md](memo/algorithm.md) |
| `decompose` | combine | ∧/∨ | split, label parts, recombine | [decompose/algorithm.md](decompose/algorithm.md) |

## Laws

- **⊕ `first_success`** — associative; unit is the always-declining leaf; the walk
  stops at the first non-⊥, and a `NOT_LTL` verdict is absorbing.
- **⊞ `best_of`** — walks all arms; the first `OK` is the incumbent, displaced only
  when the comparator says a later arm wins; `NOT_LTL` absorbing. With the trivial
  "always-beats" comparator it degenerates to "last OK"; the choice of comparator is
  the only policy.
- **∘ `compose`** — `(Decorator, ∘, identity)` is a monoid: associative, with
  `identity` neutral.
- **fix `recurse`** — `recurse(step)` is the translator `leaf` satisfying
  `leaf = step(leaf)`; it adds no behaviour of its own (termination and the floor are
  `step`'s).
- **`memo`** — identity on results (same formula/status/tags); purely operational.
- **∧/∨ `decompose`** — `decompose(split, connective, tag)(child)` splits the language,
  labels each part with `child`, and recombines under `∧`/`∨`; a declined part declines
  the whole. Faithful iff `split` is a genuine language (de)composition for the
  connective.

`first_success` and `best_of` are the two *choice* combinators (differing only in the
selection rule); `recurse` is their *self-reference* complement; `compose` and `memo`
are *decorators*; `decompose` is the *combine* operator. The concrete splits that feed
`decompose` (strength / acceptance / scc) are domain code and stay in
`aut2ltl/decomp/`.

## Index

The package `__init__` re-exports the public surface as a one-stop facade —
`from aut2ltl.combinators import first_success, best_of, compose, identity, recurse, Memo, decompose`
— while the submodule paths (`aut2ltl.combinators.<brick>`) remain importable.
