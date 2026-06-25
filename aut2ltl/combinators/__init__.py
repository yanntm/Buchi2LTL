"""aut2ltl.combinators — the general-purpose Translator-algebra bricks (the index).

Five combinators, each general over the contract (knows no engine), each with its own
`algorithm.md`:

  - `first_success` (⊕)  choice: first non-declined result;
  - `best_of`       (⊞)  choice-by-size: the result a comparator prefers;
  - `compose`       (∘)  decorator composition, unit `identity`;
  - `recurse`      (fix)  self-reference: `leaf = step(leaf)`, the recursive descent;
  - `Memo`               sharing decorator (one child run shared across call sites).

Soundness (faithful-or-decline) is closed under every one, so any term built from them
is sound by construction. This module re-exports the public surface as a one-stop
facade; the submodule paths (`aut2ltl.combinators.<brick>`) remain importable. See
README.md for the algebra and law table.
"""
from __future__ import annotations

from .first_success import first_success
from .best_of import best_of, Comparator, smaller, significantly_smaller
from .compose import compose, identity
from .recurse import recurse
from .memo import Memo
from .decompose import decompose, combine, Connective, Split

__all__ = [
    "first_success",
    "best_of", "Comparator", "smaller", "significantly_smaller",
    "compose", "identity",
    "recurse",
    "Memo",
    "decompose", "combine", "Connective", "Split",
]
