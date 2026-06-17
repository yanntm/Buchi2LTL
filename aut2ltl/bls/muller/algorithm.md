# The Muller (general-case) cascade translator

The fallback leaf of the kr cascade engine: the full, general Δ₂ **Muller-DNF**
construction. It accepts every cascade an LTL-definable language produces — the
dispatch chain reaches it only when no simpler acceptance class (`acc` / `weak` /
`buchi` / `cobuchi`) applies — and never declines in practice (LTL input is
counter-free). It is the explosive-but-complete form; the simpler members exist to
avoid it where they can.

## Setting

```
Label             =  Some φ  |  ⊥                  -- φ an LTL formula; ⊥ = decline
CascadeTranslator =  CascadeHolder → Label
```

See [`kr/cascade_translator.py`](../cascade_translator.py) and the adapter
[`kr/aut2cas.py`](../aut2cas.py).

## The formula

The lifted Müller condition is a family of **good config-sets** `M` — the recurrent
sets the normalized D actually exhibits (`good_muller_sets`). A run accepts iff the
set of configurations it visits infinitely often is *exactly* some good `M`:

```
φ  =  ⋁_{M good}  ( ⋀_{C ∈ M} ¬Fin(C)  ∧  ⋀_{C ∉ M} Fin(C) )
```

with `Fin(C)` the "only finitely often in configuration `C`" formula (Lemma 7;
[`kr/fin.py`](../fin.py), built on the five inductive reachability operators in
[`kr/reachability_operators.py`](../reachability_operators.py)). Each disjunct pins
the infinity-set to one good `M`; the disjunction covers all of them.

**Fin-reach fold** (default; `KR_FOLD_FIN_REACH=0` restores the full term): for a good
`M`, a run with `Inf ⊇ M` has a strongly-connected infinity-set, so any visited `C` is
reachable from `M` — hence a `C` unreachable from `M` is visited finitely and its
`Fin(C)` is already implied. Those conjuncts are dropped *before* building `fin_c`
(the explosive step), so dropped configs cost nothing.

## Degenerate cases

- A trivial cascade (`num_levels == 0`) collapses to `⊤`/`⊥` by the acceptance of the
  normalized D.
- An empty good-set family ⇒ the empty disjunction ⇒ `φ = false` (empty language).

## Soundness & cost

Exact for any LTL-definable ω-regular language (the construction is complete), but the
flat form is **exponential** in the configuration count — this is the size cost the
whole portfolio exists to avoid where a structured fragment applies. The hash-consed
DAG shares the repeated `Fin(C)` sub-terms (each computed once, reused across
disjuncts).
