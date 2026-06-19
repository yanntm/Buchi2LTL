"""normalize — small self-contained AP-normalisation + dedup services.

Two normalisers (`names`, `polarity`) and a folder-walking `dedup` engine that
takes either as a pluggable key. Orthogonal to sample collection: it does not
generate the corpus. `dedup` reports by default (dry run); its `--prune` is the
explicit opt-in that removes duplicates.
"""
from __future__ import annotations

from .names import (  # noqa: F401
    normalize_hoa,
    normalize_ltl,
    normalize_text,
    _is_hoa_text,
)
from .polarity import (  # noqa: F401
    hoa_flips,
    ltl_flips,
    polarity_normalize_hoa,
    polarity_normalize_ltl,
    polarity_normalize_text,
)
