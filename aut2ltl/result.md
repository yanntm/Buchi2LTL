# Result lifecycle

The contract-floor counterpart to `sl/algorithm.md`. It specifies the result a
`Translator` returns, its **closed** status set, the two algebras for combining
results (composition `credit` / `fuse` and choice `first`), and the standard
accumulator idiom for using it. The current type is `LTLFormulaResult` in
`contract.py`; this is the spec to build/clean toward (a better-named home is part
of the cleanup — see end).

## The result

A result carries:

- `formula` — the reconstructed LTL (a `spot.formula`), present only on success;
- `technique` — the set of method tags that contributed (open set of strings);
- `status` — one of the closed values below;
- `diagnosis` — optional human-facing detail explaining a NOK (e.g. "non-aperiodic
  monoid; D was not state-minimal, so this is a strong hint, not a proof").

## Status — a closed enum

Three values.

| value | meaning | formula? |
|---|---|---|
| `OK` | success — a language-faithful formula | yes |
| `DECLINED` | the translator was unable to produce a result (optional diagnosis) | no |
| `NOT_LTL` | the language is not LTL-definable (optional diagnosis) | no |

There is no separate "probably not LTL" value. A tentative non-definability (D not
state-minimal, so possibly an artifact) is the **same status** `NOT_LTL`, with the
tentativeness stated in the `diagnosis`. Proof vs hint drives no different
behavior, so it is not a separate value — just text on a single closed enum of
three.

**Two-state view (what a consumer acts on).** `OK` vs `NOK` = `{DECLINED,
NOT_LTL}`. A consumer branches on the binary; a NOK carries its **reason** = its
status value (plus optional diagnosis).

**Three categories (what the reason means to `first`).**

- **SUCCESS** = `OK`.
- **BAIL (recoverable)** = `DECLINED`.
- **VERDICT (absorbing)** = `NOT_LTL`.

The BAIL/VERDICT split is consumed by **exactly one** combinator, `first`.

**Dominance order** (used by composition): `NOT_LTL ≻ DECLINED ≻ OK`.

## The universal consumer rule

Every consumer of a child result — `credit`, `fuse`, `sl_core`, any translator
using a sub-label — obeys one rule:

- child **OK** → credit its techniques, use its formula, keep building.
- child **NOK** → **propagate immediately, bail, report the reason** (status +
  diagnosis).

You never recover from a NOK yourself: the labeler you were handed already wrapped
whatever recovery it had (a `first` inside it); once it returns a NOK, it is final
to you.

## Usage — the accumulator idiom

A procedure that produces a result holds **one** current result and threads it:

1. **Start** in `OK`, crediting yourself — seed it with your own technique tag.
2. **Delegate**: whenever you call a delegate translator / a method that returns a
   result, **credit it into your instance**. If your instance is now NOK,
   **bail — return it as is** (it already carries the right status, diagnosis, and
   accumulated techniques).
3. **Finish**: if you reach the end still `OK`, fill in the `formula` field and
   return.
4. **Error**: at any point you may set your instance to a NOK status (with an
   optional diagnosis) and return it.

```
res = Result.ok(MY_TAG)                  # start OK, credit yourself
for sub in delegates:
    res.credit(sub(...))                 # fold a child in (mutating accumulator)
    if res.nok: return res               # bail with the reason
res.formula = build(...)                 # finish: fill the formula
return res
                                         # on error: res.fail(NOT_LTL, diag); return res
```

The accumulator is a **per-call local**, never shared, so the mutation is safe
(MT-safe by construction).

## Composition monoid: `credit` / `fuse`

`credit` folds a child into the current result. Identity is `OK`; the dominance
order is the join.

```
res.credit(other):                       -- mutates res, returns res (for chaining)
    other OK   → technique = res ∪ other          (stay OK, keep res.formula)
    other NOK  → res takes other's status + diagnosis; formula cleared

fuse(primary, *others) = primary.credit(o1).credit(o2)…
```

Properties: associative, `OK` identity, `NOT_LTL` absorbing (max by `NOT_LTL ≻
DECLINED ≻ OK`). A bail credits **no** techniques — a NOK contributes only its
reason.

## Choice monoid: `first`

The chain-of-responsibility. Identity is `decline` (the empty NOK). It is the
**single** combinator that inspects more than OK/NOK, and it deviates from the
universal rule in **exactly one** case:

```
first(a, b)(x) = let r = a(x) in
                 if r.status == DECLINED then b(x)   -- THE one deviation: recover a decline
                 else r                               -- OK or NOT_LTL: return as-is (reason kept)

first([s₁..sₙ]) = foldr first decline [s₁..sₙ]        -- decline closes the chain
```

So `first` is just the universal consumer with one change: a `DECLINED` becomes
"try the next member" instead of bailing. Every other NOK still bails with its
reason — a `NOT_LTL` short-circuits the chain (the next member is wasted, no
formula exists, and trying it would *lose the reason*). `first` does **not** credit
the techniques of the declined members it skips; it returns the winning `OK` (or a
propagated `NOT_LTL`, or the terminal `decline`) unchanged.

`decline` as the last element is the identity precisely because it is the NOK that
says "I have nothing and no opinion": the thing `first` recovers *from*, and the
honest landing when the list runs out. A `NOT_LTL` terminal would be wrong — nobody
proved impossibility.

## The duality

```
combinator   role          continue on    identity      rule
---------    -----------   -----------    ---------     -----------------------------------------
first        choice        DECLINED       decline (⊥)   first non-declined wins; NOT_LTL short-circuits
credit/fuse  composition   (folds all)    OK            max-status wins; OK identity; NOT_LTL absorbing
```

`first` skips declines until something sticks; `credit` keeps everything OK and
bails on the worst. Choice has `decline` as unit; composition has `OK` as unit.
The `DECLINED`-vs-`NOT_LTL` distinction exists *only* to tell `first`
recover-vs-propagate.

## Consequence for `sl_core`

`sl_core` is a consumer in the accumulator idiom: start `OK` with `{"sl"}`, credit
each child, bail on NOK (propagating the exact reason), else fill `Or(stay, leave)`
and return. Today it flattens a child `NOT_LTL` to `DECLINED` (`if not res.ok:
return decline`) — wrong by this model, since a `first` above would keep trying
members that cannot succeed. The accumulator `credit` fixes this for free.

## Naming / home

`contract.py` mixes the result struct with the `Translator` / `CascadeTranslator`
protocols and is hard to find. The result type + `Status` + `credit`/`fuse` want a
result-named module (e.g. `result.py`); the protocols can stay in the contract
floor. To settle at implementation.
