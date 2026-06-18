"""aut2ltl.best_of — the choice-by-size combinator brick (see README.md)."""
from __future__ import annotations

from .best_of import best_of
from .comparators import Comparator, smaller, significantly_smaller

__all__ = ["best_of", "Comparator", "smaller", "significantly_smaller"]
