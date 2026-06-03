"""
kr.gap — Focused sub-services for the GAP/SgpDec bridge.

Currently contains:
- parse : parsing of structured GAP output into Cascade objects.

This subpackage keeps the individual files small and each module
focused on one service (generation, execution, parsing, etc.).
"""

from .parse import parse_cascade_output

__all__ = ["parse_cascade_output"]
