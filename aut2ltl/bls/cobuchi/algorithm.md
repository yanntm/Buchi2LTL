# The coBüchi cascade translator

A leaf of the kr cascade engine and the **dual of [`buchi`](../buchi)**: it reads the
LTL of a coBüchi (persistence, Σ₂) automaton off the Krohn-Rhodes cascade as a
conjunction of "finitely often in each marked configuration".

## Setting

```
Label             =  Some φ  |  ⊥                  -- φ an LTL formula; ⊥ = decline
CascadeTranslator =  CascadeHolder → Label
```

See [`bls/cascade_translator.py`](../cascade_translator.py) and the adapter
[`bls/aut2cas.py`](../aut2cas.py).

## When it applies

Self-gating (`is_cobuchi_cascade`): the predicate tests the **natural** acceptance
recovered via `postprocess(., "generic")`. This matters — `decompose_aut`'s parity
step hides a natural `Fin(0)` as `Inf(0)|Fin(1)` (on which `is_co_buchi` is False),
and `postprocess(., "coBuchi")` is unsound (a recurrence cascade like `GFa` would
wrongly pass). It declines otherwise.

## The formula

With `Fin(C)` the formula true on words whose run visits configuration `C` only
finitely often (Lemma 7; [`bls/fin.py`](../fin.py)), persistence is "eventually stay
out of every marked configuration":

```
φ  =  ⋀_{C ∈ markedConfigs}  Fin(C)
```

`markedConfigs` is the cover-aware `cobuchi_finite_configs()` set.

## Degenerate case

No marked configuration ⇒ the empty conjunction ⇒ `φ = true`: every run accepts.

## Soundness

Exact on the coBüchi fragment (persistence = each marked config visited finitely
often), declines otherwise — never a wrong formula. Dual to the Büchi member's
`⋁ ¬Fin(C)`.
