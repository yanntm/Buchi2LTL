"""
aut2ltl/language.py — Language: the input to a Translator.

A `Language` denotes one ω-language and hands out the automaton REPRESENTATION a
translator prefers, derived lazily and cached. All representations are
language-equivalent by construction; the object is a handle over representations,
not an abstract word-set (no set algebra — ask for a shape, get an automaton).

Two constructors are the only entry points: `Language.of(aut)` from an arbitrary
HOA automaton, and `Language.of_ltl(f)` from an LTL formula (the one place a
formula enters — it is translated to an automaton lazily, after which everything
is automaton-backed). This is the kr rule "an automaton, never a formula" made a
property of the constructor rather than of the Translator signature.

LAYERING: this is a contract-floor module. It knows spot automata and formulas
(shared dependencies, below every engine) but NOT any engine type — in particular
NOT `Cascade` (kr-specific). The cascade is built on the kr side from
`det_parity_sbacc()` (see kr/aut2cas.py); it is never a representation Language
carries, which would invert the floor -> kr layering.
"""
from __future__ import annotations

import os
from typing import Optional, Union

import spot

from aut2ltl.options import OptionSpec

# kr's census is acutely state-count sensitive, so the decomposition wants a
# state-minimal form; SAT minimization is state-optimal but exponential, so it is
# gated to small automata (our domain — explicit 2^|AP| letters, few states).
_SAT_MIN_STATES = int(os.environ.get("KR_SAT_MIN_STATES", "30"))

# The floor's tiny OPTIONS contract (one knob). Declared for discoverability; the
# call site above still reads os.environ (Bucket 3 — a process-wide perf gate, not
# instance config). `default` mirrors the in-code default.
SAT_MIN_STATES = OptionSpec(
    "language.sat_min_states", 30,
    "SAT-minimize the input automaton only at or below this state count",
    env="KR_SAT_MIN_STATES")

LANGUAGE_OPTIONS = [SAT_MIN_STATES]


class Language:
    """One ω-language, presented as several language-equivalent automaton
    representations (lazy + cached). Build with `Language.of` / `Language.of_ltl`,
    never the bare constructor."""

    def __init__(
        self,
        *,
        aut: Optional["spot.twa_graph"] = None,
        formula: Optional["spot.formula"] = None,
    ) -> None:
        # Exactly one source; use the classmethod constructors, not this directly.
        self._source_aut: Optional["spot.twa_graph"] = aut
        self._source_formula: Optional["spot.formula"] = formula
        self._cache: dict = {}

    # --- constructors (the only entry points) ---

    @classmethod
    def of(cls, aut: "spot.twa_graph") -> "Language":
        """A Language from an arbitrary HOA automaton (its language is L(aut))."""
        return cls(aut=aut)

    @classmethod
    def of_ltl(cls, f: Union[str, "spot.formula"]) -> "Language":
        """A Language from an LTL formula (string or spot.formula). The formula is
        translated to an automaton lazily on the first representation request."""
        if isinstance(f, str):
            f = spot.formula(f)
        return cls(formula=f)

    # --- base automaton (source as given, or the formula translated) ---

    def _base(self) -> "spot.twa_graph":
        """The source automaton: the HOA as given, or `formula.translate()`."""
        a = self._cache.get("base")
        if a is None:
            a = (self._source_aut if self._source_aut is not None
                 else self._source_formula.translate())
            self._cache["base"] = a
        return a

    # --- representations (lazy + cached, named by representation) ---

    def tgba(self) -> "spot.twa_graph":
        """A (generalized) Büchi automaton, NOT forced deterministic — the
        nondeterministic translate-style form the heuristic/sl engine exploits."""
        a = self._cache.get("tgba")
        if a is None:
            a = spot.postprocess(self._base(), "tgba")
            self._cache["tgba"] = a
        return a

    def det_parity_sbacc(self) -> "spot.twa_graph":
        """Deterministic, complete, min-even parity with STATE-BASED acceptance —
        the input form the Krohn-Rhodes cascade is built from (kr/aut2cas.py).
        State-based acceptance is the cascade's soundness requirement (the lifted
        Muller condition is over configurations/states)."""
        a = self._cache.get("det_parity_sbacc")
        if a is None:
            a = spot.postprocess(self._base(), "parity min even",
                                 "deterministic", "complete", "sbacc")
            self._cache["det_parity_sbacc"] = a
        return a

    def det_generic(self) -> "spot.twa_graph":
        """Deterministic automaton in GENERIC (natural) acceptance — the form on
        which coBüchi/weak recognizability is read (the parity step can hide it)."""
        a = self._cache.get("det_generic")
        if a is None:
            a = spot.postprocess(self._base(), "deterministic", "generic")
            self._cache["det_generic"] = a
        return a

    def det_generic_minimal(self) -> "spot.twa_graph":
        """`det_generic()` further STATE-minimized (SAT, gated to small automata) —
        the form the AND/strength decomposition needs. Best-effort: falls back to
        `det_generic()` on a large or unsolved automaton."""
        a = self._cache.get("det_generic_minimal")
        if a is None:
            det = self.det_generic()
            if det.num_states() <= _SAT_MIN_STATES:
                try:
                    m = spot.sat_minimize(det)
                    if m is not None and m.num_states() < det.num_states():
                        det = m
                except Exception:
                    pass
            self._cache["det_generic_minimal"] = det
            a = det
        return a


__all__ = ["Language"]
