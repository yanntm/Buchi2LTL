"""
bls/definability/witness/pin.py — pin the GAP right-action order of the lift.

The witness lift (`witness._induced_transform`) reads a `Factorization` index word
left-to-right through the transition monoid, composing in the image-list convention
(`s -> g[s]`). That is correct only if it agrees with GAP's right-action product
`gens[w0] * gens[w1] * …`; otherwise the lifted period word `v` comes out reversed
(research note §4 gotcha). A period-2 cycle cannot expose the bug — a 2-cycle equals
its inverse — and a single-letter factor word (e.g. `a;a` on the mod-3 counter) is a
palindrome, so its reversal is itself: neither tests the *direction*.

`check_action_order(lang)` pins it on two fronts, against GAP as the independent
oracle (`gap.witness_eval.eval_word`):

1. the **real** witness `factor` — `_induced_transform` must equal GAP's product;
2. a **constructed, direction-sensitive** word (`_induced_transform(w) != …(reversed
   w)`) — for which `_induced_transform` must match GAP forward *and* mismatch GAP
   on the reversal. This is the part palindromes / period-2 cannot exercise: it
   fails loudly if the composition order is flipped.

The module computes the comparison; it asserts nothing — the probe / test reports it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

import spot

from aut2ltl.bls.extract import extract_generators
from aut2ltl.bls.gap.witness_eval import eval_word
from .witness import _induced_transform, extract_witness

if TYPE_CHECKING:
    from aut2ltl.language import Language


@dataclass
class PinResult:
    """The outcome of pinning the lift's composition order against GAP.

    Field groups: the real `factor` value check, and the constructed direction check.
    `factor_*` always populated; `probe_*` are `None` when the monoid is commutative
    (`direction_vacuous`), so no direction-sensitive word exists to test."""

    p: int
    factor: List[int]
    factor_induced: List[int]
    factor_gap: List[int]
    factor_match: bool
    direction_vacuous: bool
    probe_word: Optional[List[int]] = None
    probe_induced_fwd: Optional[List[int]] = None
    probe_induced_rev: Optional[List[int]] = None
    probe_gap: Optional[List[int]] = None
    direction_correct: Optional[bool] = None

    @property
    def pinned(self) -> bool:
        """True iff the real factor matches GAP and the direction check confirms the
        left-to-right convention (forward matches, reversal does not). A commutative
        monoid (`direction_vacuous`) leaves the order unpinned."""
        return self.factor_match and self.direction_correct is True


def _find_direction_sensitive_word(gens: List[List[int]]) -> Optional[List[int]]:
    """A 1-based two-generator index word whose induced transform differs from its
    reversal, i.e. a word that actually exercises composition order, or `None` if the
    monoid is commutative (every length-2 word is order-insensitive)."""
    n = len(gens)
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            word = [i, j]
            if _induced_transform(gens, word) != _induced_transform(gens, word[::-1]):
                return word
    return None


def check_action_order(
    lang: "Language",
    *,
    gap_cmd: str = "gap",
    timeout: int = 60,
    max_aps: int = 5,
) -> Optional[PinResult]:
    """Pin the lift's GAP right-action order for a non-LTL `lang`, or `None` when the
    language carries no group (aperiodic — nothing to lift).

    Recomputes the same generators the witness lift saw (`det_generic_minimal`,
    completed) and compares `_induced_transform` to GAP's product on the real witness
    factor and on a constructed direction-sensitive word. See `PinResult`.
    """
    w = extract_witness(lang, gap_cmd=gap_cmd, timeout=timeout, max_aps=max_aps)
    if w is None:
        return None
    aut = spot.postprocess(
        lang.det_generic_minimal(), "deterministic", "generic", "complete"
    )
    gens, _masks, _vals = extract_generators(aut, max_aps=max_aps)

    factor_induced = _induced_transform(gens, w.factor)
    factor_gap = eval_word(gens, w.factor, gap_cmd=gap_cmd, timeout=timeout)
    res = PinResult(
        p=w.p,
        factor=list(w.factor),
        factor_induced=factor_induced,
        factor_gap=factor_gap,
        factor_match=(factor_induced == factor_gap),
        direction_vacuous=True,
    )

    probe = _find_direction_sensitive_word(gens)
    if probe is not None:
        fwd = _induced_transform(gens, probe)
        rev = _induced_transform(gens, probe[::-1])
        gap = eval_word(gens, probe, gap_cmd=gap_cmd, timeout=timeout)
        res.direction_vacuous = False
        res.probe_word = probe
        res.probe_induced_fwd = fwd
        res.probe_induced_rev = rev
        res.probe_gap = gap
        res.direction_correct = (fwd == gap and rev != gap)
    return res


__all__ = ["PinResult", "check_action_order"]
