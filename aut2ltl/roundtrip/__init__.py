"""
aut2ltl.roundtrip — the `Roundtrip` combinator Translator.

`Roundtrip(labeler)` labels a Language with `labeler`, re-describes the language by
the resulting formula, and labels that re-description with `labeler` again, returning
the second result (a declined first label propagates). See algorithm.md for the
construction.

Public entry: `Roundtrip`.
"""

from .roundtrip import Roundtrip

__all__ = ["Roundtrip"]
