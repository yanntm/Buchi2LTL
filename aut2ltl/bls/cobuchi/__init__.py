"""
aut2ltl.bls.cobuchi — the coBüchi (persistence, Σ₂) cascade-translator member.

`cobuchi` labels a coBüchi cascade as φ = ⋀_{marked configs C} Fin(C), the dual of
`buchi`, and declines otherwise. Membership is tested on the natural acceptance
(`postprocess(., "generic")`), since the parity step hides natural Fin(0).

Public entry: `cobuchi` (the singleton `CascadeTranslator`). See algorithm.md.
"""
from .cobuchi import is_cobuchi_cascade, CoBuchi, cobuchi

__all__ = ["is_cobuchi_cascade", "CoBuchi", "cobuchi"]
