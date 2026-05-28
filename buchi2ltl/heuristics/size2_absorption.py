"""
Size-2 Non-Accepting SCC Absorption (Fusion) Heuristic.

This module re-exports the current best implementation of the fusion test
from `fusion_heuristic.py`.

The heuristic attempts to "unfold" size-2 non-accepting SCCs into a
pseudo-linear form so that the core backward labeling rules can be applied.
"""

from .fusion_heuristic import try_absorb_size2_v2 as try_absorb_size2_nonaccepting_scc

__all__ = ["try_absorb_size2_nonaccepting_scc"]
