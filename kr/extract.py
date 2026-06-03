"""
Extract transformation generators from a Spot automaton for SgpDec.

The holonomy decomposition (and the Boker et al. LTL construction) operate on
*deterministic* (semi)automata.  This module provides helpers to turn a
deterministic Spot twa_graph into the list-of-images representation expected
by SgpDec:

    gens = [
        [delta(0, letter0), delta(1, letter0), ..., delta(n-1, letter0)],  # letter 0
        [delta(0, letter1), ... ],                                         # letter 1
        ...
    ]

Letters are concrete valuations of the atomic propositions (2^|AP| possible
letters).  For |AP| > ~5 we refuse or truncate (the semigroup becomes huge
anyway and the eventual LTL formulas are already intractable).

We only support *deterministic* automata for now.  If the input is
nondeterministic the caller must determinize first (via Spot) or the
extraction will raise.
"""

from __future__ import annotations
from typing import List, Optional, Tuple
import itertools
import spot
import buddy

from .bdd_utils import get_ap_bdd_vars, build_point_bdd as _build_point_bdd


class ExtractionError(RuntimeError):
    pass


def is_deterministic(aut: spot.twa_graph) -> bool:
    return bool(aut.prop_deterministic())


def _valuation_to_bdd(aut: spot.twa_graph, mask: int, aps: List[spot.formula]) -> "buddy.bdd":
    """Compat shim. Prefer build_point_bdd + precomputed ap_vars for new code (see bdd_utils.py)."""
    # Delegate to the robust version (will do its own discovery if no cache, but callers
    # in this file now precompute to avoid interleaving hazards).
    return _build_point_bdd(aut, mask, aps)


def extract_generators(
    aut: spot.twa_graph,
    *,
    max_aps: int = 5,
    include_all_letters: bool = True,
) -> Tuple[List[List[int]], List[int], List[Dict[str, bool]]]:
    """
    Return (generators, letter_masks, valuations) for a deterministic automaton.

    generators : list of image lists (0-based targets for each original state).
    letter_masks : the integer bitmasks corresponding to each generator.
    valuations : list of {'p': bool, ...} dicts for each letter (for LTL guards).

    Raises ExtractionError if the automaton is not deterministic or too many APs.
    """
    if not is_deterministic(aut):
        raise ExtractionError(
            "extract_generators requires a deterministic automaton "
            "(aut.prop_deterministic() must be true). "
            "Use Spot's 'Deterministic' option or determinize first."
        )

    aps = list(aut.ap())
    n = aut.num_states()
    if len(aps) > max_aps:
        raise ExtractionError(
            f"Too many atomic propositions ({len(aps)} > {max_aps}). "
            "The transformation semigroup on 2^|AP| letters will be enormous; "
            "reduce |AP| or set max_aps higher at your own risk."
        )

    num_letters = 1 << len(aps)
    gens: List[List[int]] = []
    masks: List[int] = []

    # For speed we precompute, for each state, a map from concrete mask -> successor.
    # If the aut is not complete on a letter from a state (no edge), we map to a
    # dedicated dead rejecting trap state. This keeps the language correct
    # (undefined letters do not allow spurious continuation to accepting runs).
    # The generators are then total transformations on 0..n (dead = n).

    warned_incomplete = False
    dead = n  # extra dead rejecting trap state for proper completion of incomplete auts (critical for correct language)

    # Precompute AP -> buddy var map *once*, before any per-letter BDD construction.
    # This avoids the old hazard of doing var discovery (tiny .translate()) interleaved
    # with (e.cond & point_bdd) on the main aut, which was a source of sporadic segfaults
    # in buddy/spot C extensions (especially visible after adding dead-trap states).
    ap_vars = get_ap_bdd_vars(aut)

    for mask in range(num_letters):
        images = [0] * (n + 1)
        point_bdd = _build_point_bdd(aut, mask, aps, ap_vars=ap_vars)
        for s in range(n):
            succ = None
            for e in aut.out(s):
                # Does this edge fire under the concrete letter?
                if (e.cond & point_bdd) != buddy.bddfalse:
                    if succ is not None:
                        # Should not happen on a deterministic aut
                        raise ExtractionError(f"Non-deterministic choice for state {s} under mask {mask}")
                    succ = e.dst
            if succ is None:
                if not warned_incomplete:
                    warned_incomplete = True
                succ = dead
            images[s] = succ
        images[dead] = dead  # dead is permanent trap
        gens.append(images)
        masks.append(mask)

    if warned_incomplete:
        # We do not raise — the decomposition can still be computed.
        # Dead state makes the language correct (no spurious continuations on undefined letters).
        pass

    valuations = [mask_to_valuation(m, [str(ap) for ap in aps]) for m in masks]
    return gens, masks, valuations


def num_concrete_letters(num_aps: int) -> int:
    return 1 << num_aps


def pretty_letter(mask: int, aps: List[str]) -> str:
    """Return a human string like 'p0 & !p1' for a mask."""
    parts = []
    for i, name in enumerate(aps):
        bit = bool(mask & (1 << i))
        parts.append(name if bit else f"!{name}")
    return " & ".join(parts) if parts else "1"


def mask_to_valuation(mask: int, aps: List[str]) -> Dict[str, bool]:
    """Return {'p': True, 'q': False, ...} for the mask (bit i corresponds to aps[i])."""
    return {name: bool(mask & (1 << i)) for i, name in enumerate(aps)}
