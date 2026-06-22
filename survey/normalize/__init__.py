"""normalize — small self-contained AP-normalisation + dedup services.

Two normalisers (`names`, `polarity`) plus a folder-walking `dedup`/`canon` pair on
the shared `sweep` engine. Orthogonal to sample collection: it does not generate a
corpus. The folder tools report by default (dry run); `--prune` writes.

The public normaliser functions are re-exported **lazily** (PEP 562): the `names`
and `polarity` submodules are imported on first attribute access, so running one as
`python -m survey.normalize.<mod>` does not double-import it (no runpy warning).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

# public attribute -> submodule that provides it (imported on first access)
_LAZY = {
    "normalize_hoa": "names", "normalize_ltl": "names",
    "normalize_text": "names", "_is_hoa_text": "names",
    "hoa_flips": "polarity", "ltl_flips": "polarity",
    "polarity_normalize_hoa": "polarity", "polarity_normalize_ltl": "polarity",
    "polarity_normalize_text": "polarity",
}

__all__ = list(_LAZY)


def __getattr__(name: str):
    if name in _LAZY:
        import importlib
        mod = importlib.import_module(f"{__name__}.{_LAZY[name]}")
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:  # keep the surface visible to type checkers / IDEs
    from survey.normalize.names import (  # noqa: F401
        _is_hoa_text, normalize_hoa, normalize_ltl, normalize_text,
    )
    from survey.normalize.polarity import (  # noqa: F401
        hoa_flips, ltl_flips, polarity_normalize_hoa,
        polarity_normalize_ltl, polarity_normalize_text,
    )
