"""
aut2ltl.roundtrip — the `Roundtrip` combinator Translator and its `Finder` contract.

`Roundtrip(labeler, finder)` labels a Language with `labeler`, lets `finder` pick a
node of the resulting formula, relabels that node's language with `labeler`, and
relinks the result in place. See algorithm.md; the concrete finders live in
`cutpoints/`.

Public entries: `Roundtrip`, `Finder`.
"""

from .finder import Finder
from .roundtrip import Roundtrip

__all__ = ["Roundtrip", "Finder"]
