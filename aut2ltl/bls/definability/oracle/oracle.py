"""
bls/definability/oracle/oracle.py — the entry: the exact LTL-definability decision.

`decide(lang)` runs the pipeline of `algorithm.md` and returns a three-outcome
verdict: **LTL** (the syntactic ω-semigroup is aperiodic — a theorem),
**NOT_LTL** (a counting family, replayed against the input), or
**INCONCLUSIVE** (a resource cap or an internal failure — never a blind spot).

This is the only impure module of the package: it owns every cap and timeout,
sequences the pure workers, maps each failure to its INCONCLUSIVE reason, and
hands the family to the engine-agnostic replay before asserting anything.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, TYPE_CHECKING

import spot

from aut2ltl.verifier import verify
from ...extract import extract_generators
from ...gap.aperiodic import is_aperiodic_gens
from ..witness.enriched import letter_elems
from .closure import close
from .family import assemble
from .profile import profile
from .quotient import find_group
from .refine import chase, refine
from .residuals import state_classes

if TYPE_CHECKING:
    from aut2ltl.language import Language
    from aut2ltl.witness import Witness

LTL = "LTL"
NOT_LTL = "NOT_LTL"
INCONCLUSIVE = "INCONCLUSIVE"


@dataclass
class OracleVerdict:
    """The oracle's answer: `answer` is one of `LTL` / `NOT_LTL` /
    `INCONCLUSIVE`, `reason` says on what grounds, `witness` carries the
    replayed counting family on the negative answer (and only there)."""

    answer: str
    reason: str
    witness: Optional["Witness"] = None


def decide(
    lang: "Language",
    *,
    gap_cmd: str = "gap",
    gap_timeout: int = 30,
    max_aps: int = 5,
    em_cap: int = 20000,
) -> OracleVerdict:
    """Decide LTL-definability of `lang`'s ω-language exactly, up to the caps.

    Screen (transition-monoid aperiodicity, GAP) → enriched-monoid closure →
    congruence (residual classes + profiles, right refinement) → aperiodicity
    of the quotient → on a group, chase + family assembly + replay against the
    input automaton. Every cap or failure degrades to INCONCLUSIVE."""
    try:
        det = lang.det_generic_minimal()
        aut = spot.postprocess(det, "deterministic", "generic", "complete")
        gens, _masks, valuations = extract_generators(aut, max_aps=max_aps)
    except Exception as exc:
        return OracleVerdict(INCONCLUSIVE, f"no deterministic letter form: {exc}")

    try:  # the screen is a shortcut, never a blocker: unrunnable ⟹ skipped
        if is_aperiodic_gens(gens, gap_cmd=gap_cmd, timeout=gap_timeout):
            return OracleVerdict(
                LTL, "the transition monoid is aperiodic (screen): the language "
                     "is star-free, an LTL formula exists")
    except Exception:
        pass

    try:
        letters = letter_elems(aut, valuations)
        mon = close(letters, aut.num_states(), em_cap)
        if mon is None:
            return OracleVerdict(
                INCONCLUSIVE, f"the enriched monoid exceeds the cap ({em_cap} elements)")

        st_cls = state_classes(aut)
        lin = [tuple(st_cls[st] for (st, _m) in el) for el in mon.elems]
        acc = aut.acc()
        prof = [profile(acc, el) for el in mon.elems]
        seed: List[Tuple[Tuple[int, ...], Tuple[bool, ...]]] = list(zip(lin, prof))

        cls = refine(mon, seed)
        group = find_group(mon, cls)
        if group is None:
            return OracleVerdict(
                LTL, "the syntactic ω-semigroup is aperiodic: the language is "
                     "star-free, an LTL formula exists")

        b = chase(mon, seed, group.powers[group.a - 1], group.powers[group.a])
        if b is None:
            return OracleVerdict(
                INCONCLUSIVE, "internal: a separated pair of powers did not chase")
        witness = assemble(aut, gens, valuations, mon, lin, prof, group, b)
        if witness is None:
            return OracleVerdict(
                INCONCLUSIVE, "internal: the family did not assemble from the chase")
    except Exception as exc:
        return OracleVerdict(INCONCLUSIVE, f"the oracle raised: {exc}")

    ok, _pattern = verify(lang.tgba(), witness)
    if ok:
        return OracleVerdict(
            NOT_LTL, f"a counting family with period {witness.p}, certified by "
                     f"replay against the input, toggles membership with n mod "
                     f"{witness.p}: the language is not LTL-definable",
            witness=witness)
    return OracleVerdict(
        INCONCLUSIVE, "the completed family failed replay against the input "
                      "(transport corruption); no verdict is asserted")


__all__ = ["OracleVerdict", "decide", "LTL", "NOT_LTL", "INCONCLUSIVE"]
