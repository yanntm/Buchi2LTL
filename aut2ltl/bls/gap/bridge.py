"""
kr/gap/bridge.py — high-level orchestration for SgpDec holonomy decompositions.

This is the pure, module-level API of the GAP bridge. It wires the focused
sub-services into the two entry points the rest of kr calls:

    decompose_gens : generator images        -> Cascade
    decompose_aut  : caller spot automaton   -> Cascade

The heavy/IO-bound work lives in siblings, kept out of this file on purpose:
- kr/gap/export.py : GAP-source generation (generate_gap_script)
- kr/gap/runner.py : process spawn (run_gap_script, check_gap_available)
- kr/gap/parse.py  : structured-output parser (parse_cascade_output -> Cascade)

See also:
- kr/cascade.py : the result data model + config automaton helpers
- kr/extract.py : Spot aut -> generator images (assumes complete deterministic input)
"""

from __future__ import annotations
from typing import List

from ..cascade import Cascade
from ..extract import extract_generators, ExtractionError, is_deterministic
from .export import generate_gap_script
from .runner import run_gap_script, check_gap_available  # noqa: F401 (re-exported)
from .parse import parse_cascade_output  # noqa: F401 (re-exported)

import spot


def decompose_gens(
    generators: List[List[int]],
    *,
    gap_cmd: str = "gap",
    timeout: int = 180,
) -> Cascade:
    """Run the full pipeline on an explicit list of generator images."""
    script = generate_gap_script(generators)
    raw = run_gap_script(script, gap_cmd=gap_cmd, timeout=timeout)
    return parse_cascade_output(raw, generators=generators)


def decompose_aut(
    aut: "spot.twa_graph",
    *,
    gap_cmd: str = "gap",
    timeout: int = 180,
    max_aps: int = 5,
) -> Cascade:
    """
    End-to-end: caller aut → Spot normalization to a deterministic complete
    minimized parity automaton (min even, via postprocess "parity min even",
    "deterministic", "complete") → generators → GAP (SgpDec holonomy) → Cascade.

    IMPORTANT (per current design): Spot transformations (including any state
    additions for determinization/completion/minimization) are expected and
    normal. The resulting deterministic automaton *is* the authoritative input
    D for the rest of the algorithm (Krohn-Rhodes decomp, reachability formulas,
    Fin(C), Muller DNF assembly). The homomorphism h (state_to_config) and
    acceptance lifting are defined with respect to *this* D's states and
    acceptance condition.

    The caller's original (possibly non-det, Buchi-style) aut is *not* used
    for the construction. Callers should keep it aside themselves only if
    they want a final language-equivalence check (spot.are_equivalent) after
    reconstruction. The LTL we produce is for the language of the normalized D
    (which is equivalent to the original by Spot's postprocess guarantees).

    Completion (and determinization if needed) is handled by Spot; any sink
    that appears is just a normal state. The algebraic construction treats
    everything uniformly via configs. No manual dead-trap.

    This is the standardized input contract for the KR path.
    """
    # Normalize to deterministic complete minimized parity using Spot.
    # This normalized det aut *is* our working D for decomp + reachability + Fin + assembly.
    # "sbacc" (state-based acceptance) is required for soundness: the Muller
    # condition we lift is over configurations (states), so the set of
    # infinitely-visited states must determine acceptance. With Spot's default
    # transition-based marks, a state can carry both accepting and rejecting
    # out-edges (e.g. the 1-state DPA for GFa), and the state-level Muller view
    # cannot distinguish accepting from rejecting runs.
    aut = spot.postprocess(aut, "parity min even", "deterministic", "complete", "sbacc")

    if not is_deterministic(aut):
        raise ExtractionError(
            "decompose_aut requires a deterministic automaton. "
            "The input could not be determinized to parity."
        )

    gens, masks, valuations = extract_generators(aut, max_aps=max_aps)
    casc = decompose_gens(gens, gap_cmd=gap_cmd, timeout=timeout)
    # Enrich the cascade with letter/valuation data needed for LTL encoding
    casc.aps = [str(ap) for ap in aut.ap()]
    casc.letter_masks = masks
    casc.letter_valuations = valuations
    casc.original_aut = aut  # the normalized det parity aut (our D)
    return casc
