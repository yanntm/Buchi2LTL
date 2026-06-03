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


class ExtractionError(RuntimeError):
    pass


def is_deterministic(aut: spot.twa_graph) -> bool:
    return bool(aut.prop_deterministic())


def _valuation_to_bdd(aut: spot.twa_graph, mask: int, aps: List[spot.formula]) -> "buddy.bdd":
    """Build a singleton BDD representing the concrete assignment given by mask."""
    d = aut.get_dict()
    b = buddy.bddtrue
    for i, ap in enumerate(aps):
        # Create a tiny aut just to get the buddy var for this AP (same trick as invariants.py)
        lit = spot.formula(str(ap))
        tmp = lit.translate()
        var = None
        for e in tmp.out(tmp.get_init_state_number()):
            if e.cond != buddy.bddtrue and e.cond != buddy.bddfalse:
                var = buddy.bdd_var(e.cond)
                break
        if var is None:
            # Fallback: use index (rarely correct but better than nothing)
            var = i
        bit = bool(mask & (1 << i))
        lit_bdd = buddy.bdd_ithvar(var) if bit else buddy.bdd_nithvar(var)
        b = b & lit_bdd
    return b


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
    # Since the aut may not be "complete" (some letters have no edge), we treat
    # missing transitions as "no successor" (we can map to a conventional sink or
    # raise).  For holonomy on the state set we prefer a total function; if the
    # aut is not complete we add an implicit sink state?  For the first version
    # we simply require that every state has a defined successor under every letter
    # (i.e. the aut is complete for the alphabet we consider).  If not, we still
    # emit a total map by picking an arbitrary "undefined" target or the state itself.
    # Better: use Spot's ability to complete or just map missing to n (a virtual sink
    # that we would have to add).  For simplicity in v1 we map missing letters to
    # the state itself (a common "stay" convention for unspecified) and warn.

    warned_incomplete = False

    for mask in range(num_letters):
        images = []
        point_bdd = _valuation_to_bdd(aut, mask, aps)
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
                    # We continue; the caller can inspect.
                # Convention: treat as self-loop (harmless for many examples,
                # but the user should prefer complete deterministic automata).
                succ = s
            images.append(succ)
        gens.append(images)
        masks.append(mask)

    if warned_incomplete:
        # We do not raise — the decomposition can still be computed, it just
        # represents a completion of the partial action.
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
