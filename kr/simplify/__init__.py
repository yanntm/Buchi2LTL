"""
kr/simplify — generic LTL simplification rules over spot.formula DAGs.

Independent of the kr/ decomposition; see README.md for the rule catalog,
lineage and soundness notes.
"""

from .context_pass import context_simplify

__all__ = ["context_simplify"]
