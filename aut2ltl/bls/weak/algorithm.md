# The weak (Δ₁) cascade translator

A leaf of the kr cascade engine for **weak-recognizable** languages (the obligation
level Δ₁ — safety, guarantee, and their boolean combinations). It reads the language
off the configuration automaton purely by *reachability*, no `Fin`: a run accepts iff
it settles in an accepting SCC of the configurations.

## Setting

```
Label             =  Some φ  |  ⊥                  -- φ an LTL formula; ⊥ = decline
CascadeTranslator =  CascadeHolder → Label
```

See [`bls/cascade_translator.py`](../cascade_translator.py) and the adapter
[`bls/aut2cas.py`](../aut2cas.py).

## When it applies

Self-gating (`is_weak_cascade`): the predicate tests the **natural** automaton
recovered via `postprocess(., "generic")` (the parity step can destroy weakness) with
Spot's `is_weak_automaton`. It declines otherwise.

> Off by default in the dispatch chain (`KR_DISPATCH_WEAK`): weak languages are also
> Büchi/coBüchi-recognizable and those members produce smaller formulas, so this is a
> reach-driven A/B alternative rather than the default.

## The formula

Over the SCCs of the configuration automaton, with `reach_to(ι, C)` = "the run
reaches configuration `C` from the initial config ι" (pure reach, `β = false`, no
`Fin`; §9.1 shorthand over `reach_strong`):

```
φ        =  ⋁_{G accepting SCC}  end_in(G)
end_in(G) =  ( ⋁_{C ∈ G}  reach_to(ι, C) )  ∧  ( ⋀_{C' ∈ G'}  ¬reach_to(ι, C') )
```

where `G' =` configurations reachable from `G` but not in `G`. The first conjunct
enters `G`; the second forbids leaving it — together the run must **settle** in `G`.
This subsumes looping-Büchi (safety) and looping-coBüchi (guarantee).

## Degenerate case

No accepting SCC ⇒ the empty disjunction ⇒ `φ = false` (empty language).

## Soundness

Exact on the weak fragment (settle-in-an-accepting-SCC is the weak acceptance
reading), declines otherwise — never a wrong formula.
