# Result lifecycle

The contract-floor counterpart to `sl/algorithm.md`. It specifies the result a
`Translator` returns, its **closed** status set, and the two algebras for
combining results: **composition** (`credit` / `fuse`) and **choice** (`first`).
The current type is `LTLFormulaResult` in `contract.py`; this doc is the spec to
build/clean toward (a better-named home is part of the cleanup — see end).

## The result

A result carries:

- `formula` — the reconstructed LTL (a `spot.formula`), present only on success;
- `technique` — the set of method tags that contributed (open set of strings);
- `status` — one of the closed values below;
- `note` — human-facing detail (e.g. the non-aperiodic-monoid reason for a verdict).

## Status — a closed enum

Four values. They are a closed set → a real `enum`, not loose strings.

| value | meaning | formula? |
|---|---|---|
| `OK` | success — a language-faithful formula | yes |
| `DECLINED` | "not my method" | no |
| `PROBABLY_NOT_LTL` | impossibility *hint* (D not state-minimal — may be an artifact) | no |
| `NOT_LTL` | impossibility *proof* (D minimal, non-aperiodic monoid) | no |

**Two-state view (what a consumer acts on).** There is exactly one good state and
the rest:

- **OK** — cool.
- **NOK** = `{DECLINED, PROBABLY_NOT_LTL, NOT_LTL}` — not cool.

A consumer branches on the binary, but a NOK carries its **reason** = the precise
NOK value.

**Three categories (what the reason means).**

- **SUCCESS** = `OK`.
- **BAIL (recoverable)** = `DECLINED` — "try another method."
- **VERDICT (absorbing)** = `NOT_LTL`, `PROBABLY_NOT_LTL` — "no formula exists, stop."

The BAIL/VERDICT split is consumed by **exactly one** combinator, `first` (below);
to everyone else there is only OK vs NOK.

**Dominance order** (used by composition):

```
NOT_LTL  ≻  PROBABLY_NOT_LTL  ≻  DECLINED  ≻  OK
```

## The universal consumer rule

Every consumer of a child result — `credit`, `fuse`, `sl_core`, any translator
that uses a sub-label — obeys one rule:

- child **OK** → credit its techniques, use its formula, keep building.
- child **NOK** → **retropropagate immediately, bail, and report the reason** (the
  precise NOK value).

You never recover from a NOK yourself. The labeler you were handed already wrapped
whatever recovery it had (a `first` inside it); once it hands you a NOK, it is
final to you.

## Composition monoid: `credit` / `fuse`

Combine results you *used together* (e.g. a formula built from child labels).
Identity is `OK`; the order above is the join.

```
credit(self, other):                       -- self is building; other is a child it used
    OK    & OK     → OK, formula = self.formula, technique = self ∪ other
    otherwise      → max-status wins (the worst child), propagated with its reason/note
                     (no formula; verdict carries its note)

fuse(primary, *others) = foldl credit primary others
```

Properties: associative, `OK` identity, `NOT_LTL` absorbing. This is the
"⊥-dominates" rule, generalized: the most-absorbing status wins.

Open points (decide at implementation):
1. **Conclusiveness on credit.** Crediting a *conclusive* `NOT_LTL` child into a
   larger result: stay `NOT_LTL` (impossibility propagates upward) or downgrade to
   `PROBABLY_NOT_LTL` (the proof was about the child's minimal D, not the parent's)?
   Leaning: propagate, but this only affects how loudly we claim a proof.
2. **Declined provenance.** A bail credits **no** techniques (the universal rule:
   NOK contributes only its reason, not its tags).

## Choice monoid: `first`

The chain-of-responsibility. Identity is `decline` (the empty-NOK). It is the
**single** combinator that "inspects more" than OK/NOK — and it deviates from the
universal rule in **exactly one** case:

```
first(a, b)(x) = let r = a(x) in
                 if r.status == DECLINED then b(x)   -- THE one deviation: recover a decline
                 else r                               -- OK or VERDICT: return as-is (reason kept)

first([s₁..sₙ]) = foldr first decline [s₁..sₙ]        -- decline closes the chain
```

So `first` is just the universal consumer with one change: **a `DECLINED`
becomes "try the next member" instead of bailing.** Every other NOK still bails
with its reason — a `VERDICT` short-circuits the chain (trying the next member is
wasted, no formula exists, and it would *lose the reason*). `first` does **not**
credit the techniques of the declined members it skipped; it returns the winning
`OK` (or the propagated `VERDICT`, or the terminal `decline`) unchanged.

`decline` as the last element is the identity precisely because it is the NOK that
says "I have nothing and no opinion": the thing `first` recovers *from*, and the
honest landing when the list runs out ("none of us could"). A `VERDICT` terminal
would be wrong — nobody proved impossibility.

## The duality

```
combinator   role          continue on    identity      rule
---------    -----------   -----------    ---------     -------------------------------
first        choice        DECLINED       decline (⊥)   first non-declined wins; verdict short-circuits
credit/fuse  composition   (folds all)    OK            max-status wins; OK identity; NOT_LTL absorbing
```

`first` skips declines until something sticks; `credit` keeps everything OK and
bails on the worst. Choice has `decline` as unit; composition has `OK` as unit.
The `DECLINED`-vs-`VERDICT` distinction exists *only* to tell `first` recover-vs-
propagate.

## Consequence for `sl_core`

`sl_core` is a consumer: on a child NOK it must **propagate the exact reason**.
Today it flattens a child `VERDICT` to `DECLINED` (`if not res.ok: return decline`)
— wrong by this model, since a `first` above it would then keep trying members that
cannot succeed. Once `credit`/`fuse` exist, `sl_core`'s tail becomes
`fuse(success(...), *child_results)` and the verdict propagates correctly.

## Naming / home

`contract.py` mixes the result struct with the `Translator` / `CascadeTranslator`
protocols, and is hard to find. The result type + `Status` + `credit`/`fuse` want
a result-named module (e.g. `result.py`); the protocols can stay in the contract
floor. To settle at implementation.
