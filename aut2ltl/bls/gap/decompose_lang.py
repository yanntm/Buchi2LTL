"""
kr/gap/decompose_lang.py — the Language-native entry to the GAP bridge.

`decompose_lang` is the cascade builder over a contract `Language` (the floor
input type). It pulls the det parity + state-based-acceptance form the Language
already owns — `Language.det_parity_sbacc()`, exactly the cascade input contract —
and runs the standard pipeline via `bridge.decompose_aut`. Additive over the
existing bridge: `decompose_aut` (raw spot automaton in) is untouched and stays
the per-piece entry the portfolio/surveys use.

The det normalization is idempotent (parity-min-even / deterministic / complete /
sbacc applied to an already-normalized automaton is a no-op on the language), so
routing through `decompose_aut` re-applies it harmlessly. This is the seam the
`kr/aut2cas.py` adapter uses to lift a CascadeTranslator to a Language Translator.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..cascade import Cascade
from .bridge import decompose_aut

if TYPE_CHECKING:
    from aut2ltl.language import Language


def decompose_lang(
    lang: "Language",
    *,
    gap_cmd: str = "gap",
    timeout: int = 180,
    max_aps: int = 5,
) -> Cascade:
    """Cascade from a contract `Language` (pulls `lang.det_parity_sbacc()`)."""
    return decompose_aut(
        lang.det_parity_sbacc(), gap_cmd=gap_cmd, timeout=timeout, max_aps=max_aps
    )


__all__ = ["decompose_lang"]
