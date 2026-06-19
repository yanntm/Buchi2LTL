"""
aut2ltl.bls.buchi — the Büchi (recurrence, Π₂) cascade-translator member.

`buchi` labels a Krohn-Rhodes cascade whose normalized automaton carries a plain
Büchi condition as φ = ⋁_{accepting configs C} ¬Fin(C), and declines otherwise. It
depends on the kr cascade model, the shared `Fin(C)` helper (`bls/fin.py`), and the
engine-agnostic ltl builders.

Public entry: `buchi` (the singleton `CascadeTranslator`). See algorithm.md.
"""
from .buchi import buchi, Buchi, is_buchi_cascade

__all__ = ["buchi", "Buchi", "is_buchi_cascade"]
