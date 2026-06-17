"""
aut2ltl.bls.weak — the weak (Δ₁) cascade-translator member.

`weak` reconstructs weak-recognizable languages (safety / guarantee / obligation) by
pure reachability over the configuration automaton: φ = ⋁ over accepting SCC G of
end_in(G), the run settling in G. Declines when the cascade is not weak. Off by
default in the chain (Büchi/coBüchi give smaller forms) — a reach-driven alternative.

Public entry: `weak` (the singleton `CascadeTranslator`). See algorithm.md.
"""
from .weak import is_weak_cascade, Weak, weak

__all__ = ["is_weak_cascade", "Weak", "weak"]
