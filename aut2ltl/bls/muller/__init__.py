"""
aut2ltl.bls.muller — the general Muller-DNF cascade-translator member (the BLS fallback).

`muller` is the general-case leaf: φ = ⋁_M (⋀_{C∈M} ¬Fin(C) ∧ ⋀_{C∉M} Fin(C)) over the
good config-sets M (the recurrent sets the normalized D exhibits). It is reached only
when no simpler acceptance class (acc / weak / buchi / cobuchi) applies, and never
declines in practice (LTL input is counter-free). `assemble_muller_dnf` is the
assembly it wraps.

Public entry: `muller` (the singleton `CascadeTranslator`). See algorithm.md.
"""
from .muller import assemble_muller_dnf, Muller, muller

__all__ = ["assemble_muller_dnf", "Muller", "muller"]
