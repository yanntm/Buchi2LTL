# The Acc (bounded / transient) cascade translator

A leaf of the kr cascade engine for the **bounded fragment**: cascades whose runs
reach a ⊤/⊥ sink within a bounded horizon (the "X-ladder", e.g. `X(a & X a)`). The
language from the initial configuration is then a finite unrolling — the literal
small formula — which this member emits directly, bypassing the cascade reach
machinery (no `Fin`, no reach τ-tail) that the general Muller form would pay on these
inputs.

## Setting

```
Label             =  Some φ  |  ⊥                  -- φ an LTL formula; ⊥ = decline
CascadeTranslator =  CascadeHolder → Label
```

See [`kr/cascade_translator.py`](../cascade_translator.py) for the contract and
[`kr/aut2cas.py`](../aut2cas.py) for the adapter that lifts it to a `Translator`.

## The unrolling

Indexed by configuration `c`, over the input automaton D's small per-state ⊤/⊥
oracle:

```
Acc(c)  =  ⊤                                   if L(D from state_of(c)) is universal   (R1)
        =  ⊥                                   if it is empty
        =  ⋁_σ  guard(σ) ∧ X Acc(move(c, σ))   otherwise                               (R2)
```

starting at the initial configuration ι. The ⊤/⊥ oracle is a **Spot check on the
small input automaton D** (per state, lazy + cached) — never on the output formula —
so a deciding-to-decline run pays only for the states on the path before the first
cycle. The build is memoized, `O(|reachable configs| × |Σ|)`.

## When it applies / declines

The member is **self-gating with no external predicate**: it just runs the unroll. If
a configuration is re-entered on the unroll path while it is *not* a ⊤/⊥ sink, that
config is **recurrent** — the input is outside the bounded fragment — and `Acc`
declines, so the caller falls back to the Büchi / coBüchi / Muller chain.

## Soundness

On the bounded fragment R1/R2 *are* the language equation from `ι` (a finite
unrolling to ⊤/⊥ sinks), so the emitted formula is exact; off the fragment the
recurrence is detected and the member declines — never a wrong formula.
