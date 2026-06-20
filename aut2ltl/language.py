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

As a FACTORY the constructors do two more things, transparent to the client:

  * INTERN on the literal input — a bounded LRU keyed by the canonical formula
    string / the automaton's HOA serialization — so separate calls with the same
    input return one shared `Language`, reusing its lazily-built representations
    and its definability verdict. The aim is to cache the heavy, sometimes-erratic
    spot calls (translate / postprocess), not to trust them to be cheap or to run
    twice the same. Bounded so it never hogs memory (`CACHE_SIZE`).
  * CLEAN the source once, lazily, language-preserving (`_clean` / `_base`):
    `postprocess(generic, <CLEAN_LEVEL>, any)` — Generic keeps the acceptance
    FAMILY (no degeneralization / parity), the level (default Medium) purges
    dead/unreachable states and merges redundant acceptance sets — then
    `remove_unused_ap` drops atomic propositions no edge uses (no postprocess level
    reindexes the alphabet, so we do it ourselves). A rerooted sub-language thus
    arrives smallified, which the heuristic leaves (e.g. partscc) rely on.

Both behaviours are knobs declared as `OptionSpec`s (`CLEAN_LEVEL`, `CACHE_SIZE`).

LAYERING: this is a contract-floor module. It knows spot automata and formulas
(shared dependencies, below every engine) but NOT any engine type — in particular
NOT `Cascade` (kr-specific). The cascade is built on the kr side from
`det_parity_sbacc()` (see bls/aut2cas.py); it is never a representation Language
carries, which would invert the floor -> kr layering.
"""
from __future__ import annotations

import os
from collections import OrderedDict
from typing import Callable, Optional, Tuple, Union

import spot

from aut2ltl.options import OptionSpec


class UntranslatableLanguage(Exception):
    """A formula too large to hand ltl2tgba safely — its unfolded (flat) size or
    temporal-operator count exceeds the configured bound (`TRANSLATE_TREE_LIMIT` /
    `TRANSLATE_TEMPORAL_LIMIT`). Spot's `translate` has no graceful failure on an
    exp-sized formula, so the floor REFUSES rather than dying. Unchecked, in the
    Java-`RuntimeException` sense: most call sites trust and never catch it; only
    the round trip — which deliberately re-translates a derived formula — catches
    it and DECLINES, and `main` is a last-resort net."""


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

# Input cleanup level. The gentlest spot postprocess that still tidies the input:
# Generic keeps the acceptance FAMILY (no degeneralization/parity conversion); the
# level (default Medium) controls how much it simplifies — Low only purges states,
# Medium also merges redundant acceptance sets, High also tries to shrink states;
# Any avoids size-determinism churn. Unused APs are dropped separately by `_clean`
# (no postprocess level reindexes the alphabet, to keep positional AP indices
# stable). The level is a knob so High can be tried without code changes.
_CLEAN_LEVEL = os.environ.get("AUT2LTL_CLEAN_LEVEL", "medium")

CLEAN_LEVEL = OptionSpec(
    "language.clean_level", "medium",
    "spot postprocess level for input cleanup as (generic, <level>, any): "
    "low (purge states) | medium (also merge redundant acc sets) | high (also shrink)",
    env="AUT2LTL_CLEAN_LEVEL")

# Factory cache size. Separate Language.of/of_ltl calls with the same literal input
# reuse one Language (and so its lazily-built representations + definability
# verdict). Bounded LRU so it never hogs memory; 0 disables interning.
_CACHE_SIZE = int(os.environ.get("AUT2LTL_LANG_CACHE_SIZE", "512"))

CACHE_SIZE = OptionSpec(
    "language.cache_size", 512,
    "max interned Language objects (bounded LRU over the literal of/of_ltl arg); "
    "0 disables interning",
    env="AUT2LTL_LANG_CACHE_SIZE")

# Bound on what we hand ltl2tgba (`formula.translate()` in `_base`). Spot's
# translate has no graceful failure on an exponentially large formula — it blows
# up — so we refuse one whose unfolded (flat) size or temporal-operator count is
# over budget, raising `UntranslatableLanguage` BEFORE the call. Only a
# re-presentation (the round trip) ever feeds a formula this large here; real
# inputs are tiny and never trip it. 0 disables a bound. (Bucket 3, like
# SAT_MIN_STATES: a process-wide gate, env-read; the OptionSpec is discoverability.)
_TRANSLATE_TREE_LIMIT = int(os.environ.get("KR_TRANSLATE_TREE_LIMIT", "100"))
_TRANSLATE_TEMPORAL_LIMIT = int(os.environ.get("KR_TRANSLATE_TEMPORAL_LIMIT", "32"))

TRANSLATE_TREE_LIMIT = OptionSpec(
    "language.translate_tree_limit", 100,
    "refuse ltl2tgba on a formula whose unfolded (flat) size exceeds this; 0 disables",
    env="KR_TRANSLATE_TREE_LIMIT")
TRANSLATE_TEMPORAL_LIMIT = OptionSpec(
    "language.translate_temporal_limit", 32,
    "refuse ltl2tgba on a formula whose temporal-operator count exceeds this; 0 disables",
    env="KR_TRANSLATE_TEMPORAL_LIMIT")

LANGUAGE_OPTIONS = [SAT_MIN_STATES, CLEAN_LEVEL, CACHE_SIZE,
                    TRANSLATE_TREE_LIMIT, TRANSLATE_TEMPORAL_LIMIT]


def _clean(aut: "spot.twa_graph") -> "spot.twa_graph":
    """Language-preserving input cleanup (see `CLEAN_LEVEL`). Purges unreachable /
    dead states, merges redundant acceptance sets (Medium+), keeps the acceptance
    family (Generic), then drops atomic propositions no edge uses."""
    a = spot.postprocess(aut, "generic", _CLEAN_LEVEL, "any")
    a.remove_unused_ap()
    return a


def _guard_translation(f: "spot.formula") -> None:
    """Refuse to hand ltl2tgba a formula too large to translate safely — raise
    `UntranslatableLanguage` BEFORE the call. The temporal-operator count walks the
    DAG (cheap); the unfolded (flat) size is measured with a CAP so we never unfold
    an exp tree merely to reject it — `tree_node_count` SATURATES at its `limit`, so
    we cap at limit+1 and test `> limit` to catch strict overflow. 0 disables a
    bound. The metrics import is deferred to keep the floor import-acyclic."""
    from aut2ltl.ltl.metrics import temporal_node_count, tree_node_count
    if _TRANSLATE_TEMPORAL_LIMIT and temporal_node_count(f) > _TRANSLATE_TEMPORAL_LIMIT:
        raise UntranslatableLanguage(
            f"temporal-operator count over budget (> {_TRANSLATE_TEMPORAL_LIMIT})")
    if _TRANSLATE_TREE_LIMIT and \
            tree_node_count(f, limit=_TRANSLATE_TREE_LIMIT + 1) > _TRANSLATE_TREE_LIMIT:
        raise UntranslatableLanguage(
            f"unfolded (flat) size over budget (> {_TRANSLATE_TREE_LIMIT})")


# The intern table: literal-arg key -> shared Language. Bounded LRU (insertion
# order = recency; evict oldest on overflow).
_intern_cache: "OrderedDict[str, Language]" = OrderedDict()


def _intern(key: str, build: "Callable[[], Language]") -> "Language":
    """Return the cached Language for `key`, building it once. Caching the
    expensive, sometimes-erratic spot calls (translate / postprocess) is the point
    — never trust them to be cheap or to run twice the same."""
    if _CACHE_SIZE <= 0:
        return build()
    lang = _intern_cache.get(key)
    if lang is None:
        lang = build()
        _intern_cache[key] = lang
        while len(_intern_cache) > _CACHE_SIZE:
            _intern_cache.popitem(last=False)        # evict least-recently-used
    else:
        _intern_cache.move_to_end(key)               # touch (mark most recent)
    return lang


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
        # LTL-definability verdict (definable, conclusive), or None until decided.
        # A PROPERTY of the language, but derived by the kr LtlTester (the GAP
        # aperiodicity oracle lives above this floor); Language only HOLDS the
        # tag — see `ltl_definable` / `set_ltl_definable`.
        self._ltl_definable: Optional[Tuple[bool, bool]] = None

    # --- constructors (the only entry points) ---

    @classmethod
    def of(cls, aut: "spot.twa_graph") -> "Language":
        """A Language from an arbitrary HOA automaton (its language is L(aut)).
        Interned on the automaton's literal HOA serialization, so repeated calls
        with the same input reuse one Language (and its cached representations)."""
        return _intern("A\n" + aut.to_str("hoa"), lambda: cls(aut=aut))

    @classmethod
    def of_ltl(cls, f: Union[str, "spot.formula"]) -> "Language":
        """A Language from an LTL/PSL formula (string or spot.formula). The formula is
        translated to an automaton lazily on the first representation request.
        Interned on the canonical formula string.

        When `f` is syntactically LTL, the language is LTL-definable BY CONSTRUCTION
        (we hold a defining formula), so the verdict is recorded as a proof —
        `(definable=True, conclusive=True)` — sparing the kr aperiodicity oracle. A
        PSL/SERE `f` is left undecided: its language may lie outside LTL, so the
        oracle must still rule."""
        if isinstance(f, str):
            f = spot.formula(f)

        def build() -> "Language":
            lang = cls(formula=f)
            if f.is_ltl_formula():                    # LTL ⇒ definable, by construction
                lang.set_ltl_definable(True, conclusive=True)
            return lang

        return _intern("L\n" + str(f), build)

    # --- base automaton (source as given, or the formula translated) ---

    def _base(self) -> "spot.twa_graph":
        """The source automaton — the HOA as given, or `formula.translate()` —
        after a language-preserving `_clean` (state purge, redundant-acc-set merge,
        unused-AP drop). Cleaned once, lazily, then cached. Translating a formula is
        gated by `_guard_translation`: an over-budget formula raises
        `UntranslatableLanguage` rather than blowing ltl2tgba up."""
        a = self._cache.get("base")
        if a is None:
            if self._source_aut is not None:
                raw = self._source_aut
            else:
                _guard_translation(self._source_formula)
                raw = self._source_formula.translate()
            a = _clean(raw)
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
        the input form the Krohn-Rhodes cascade is built from (bls/aut2cas.py).
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

    # --- LTL-definability tag (a property of the language; SET by the kr tester,
    #     not derived here — the GAP aperiodicity oracle lives above this floor) ---

    @property
    def ltl_definable(self) -> Optional[Tuple[bool, bool]]:
        """The cached LTL-definability verdict as `(definable, conclusive)`, or
        `None` if not yet decided. `definable` is True iff an LTL formula exists
        for this language (its syntactic monoid is aperiodic / counter-free);
        `conclusive` is True iff the verdict is a proof (decided on a genuinely
        state-minimal automaton) rather than a strong hint. Filled by the kr
        LtlTester via `set_ltl_definable`; Language never computes it itself
        (that would invert the floor -> kr layering)."""
        return self._ltl_definable

    def set_ltl_definable(self, definable: bool, *, conclusive: bool) -> None:
        """Record the LTL-definability verdict for this language (idempotent
        memo). Called by the kr LtlTester after the aperiodicity oracle runs."""
        self._ltl_definable = (definable, conclusive)


__all__ = ["Language"]
