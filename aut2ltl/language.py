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

import hashlib
import os
import sys
import time
from collections import OrderedDict
from typing import Callable, Optional, Tuple, Union

import spot

from aut2ltl.options import OptionSpec
from aut2ltl import spotrun


class UntranslatableLanguage(Exception):
    """A formula too large to hand ltl2tgba safely — its unfolded (flat) size or
    temporal-operator count exceeds the bound (`spotrun.translate_tree_limit` /
    `translate_temporal_limit`). Spot's `translate` has no graceful failure on an
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
# reuse one Language (and so its lazily-built representations + definability verdict,
# AND its object identity — which identity-keyed sharing like `decomp/inv`'s no-op
# test and `deep_nobls_memo`'s WeakKeyDictionary rely on). The prior 512 was far too
# small: a deep survey churns through many more distinct sub-languages, so entries
# were evicted and rebuilt as fresh objects mid-run, defeating that sharing. 10000
# comfortably holds a whole run. Bounded LRU so it never hogs memory; 0 disables.
_CACHE_SIZE = int(os.environ.get("AUT2LTL_LANG_CACHE_SIZE", "10000"))

CACHE_SIZE = OptionSpec(
    "language.cache_size", 10000,
    "max interned Language objects (bounded LRU over the literal of/of_ltl arg); "
    "0 disables interning",
    env="AUT2LTL_LANG_CACHE_SIZE")

# Translate tracing (diagnostic, opt-in). When AUT2LTL_LANG_TRACE is set, each
# `formula.translate()` — the one heavy, sometimes-erratic spot call on this floor —
# is timed and reported to stderr: DAG sizes in, wall time, automaton size out. All
# metrics are O(DAG); we NEVER flatten (str / tree_node_count) a formula to trace it.
# Off by default, zero overhead. Bucket 3 (env-read; OptionSpec is discoverability).
_TRACE = os.environ.get("AUT2LTL_LANG_TRACE", "") not in ("", "0")

# The `Language.of` interception (DAG in -> Language out): trace the raw input
# automaton and the resulting normalized `id`, so two translate backends handing
# in isomorphic-but-renumbered automata (raw hash differs, id same) can be told
# apart from a genuine language/structure divergence (id differs). On when
# LANGUAGE_OF_TRACE or the global TRANSLATOR_TRACE_ON is set (presence).
_OF_TRACE = "LANGUAGE_OF_TRACE" in os.environ or "TRANSLATOR_TRACE_ON" in os.environ

TRACE = OptionSpec(
    "language.trace", False,
    "trace each formula->automaton translate to stderr with its wall time and DAG "
    "sizes (in/out); off by default",
    env="AUT2LTL_LANG_TRACE")

LANGUAGE_OPTIONS = [SAT_MIN_STATES, CLEAN_LEVEL, CACHE_SIZE, TRACE]


def _fingerprint(key: str) -> str:
    """Short md5 of an intern key — the language's browsable `id`."""
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:12]


def _clean(aut: "spot.twa_graph") -> "spot.twa_graph":
    """Language-preserving input cleanup (see `CLEAN_LEVEL`). Purges unreachable /
    dead states, merges redundant acceptance sets (Medium+), keeps the acceptance
    family (Generic), then drops atomic propositions no edge uses."""
    a = spot.postprocess(aut, "generic", _CLEAN_LEVEL, "any")
    a.remove_unused_ap()
    return a


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
        lid: Optional[str] = None,
    ) -> None:
        # Exactly one source; use the classmethod constructors, not this directly.
        self._source_aut: Optional["spot.twa_graph"] = aut
        self._source_formula: Optional["spot.formula"] = formula
        self._id: Optional[str] = lid          # browsable id, stamped by of/of_ltl
        self._cache: dict = {}
        # LTL-definability reading (definable, conclusive), or None until decided
        # (`definable` itself is Optional: None = the oracle could not run).
        # A PROPERTY of the language, but derived by the kr LtlTester (the GAP
        # aperiodicity oracle lives above this floor); Language only HOLDS the
        # tag — see `ltl_definable` / `set_ltl_definable`.
        self._ltl_definable: Optional[Tuple[Optional[bool], bool]] = None

    # --- constructors (the only entry points) ---

    @classmethod
    def of(cls, aut: "spot.twa_graph") -> "Language":
        """A Language from an arbitrary HOA automaton (its language is L(aut)).
        Interned on its `canon.normalize`d HOA, so the key is a function of the
        automaton, not of its (transport-dependent) state numbering."""
        from aut2ltl.ltl import canon                  # deferred: keep the floor import-acyclic
        na = canon.normalize(aut)
        key = "A\n" + na.to_str("hoa")
        lang = _intern(key, lambda: cls(aut=na, lid=_fingerprint(key)))
        if _OF_TRACE:
            from aut2ltl.printer import format_language  # deferred: keep the floor import-acyclic
            print("[language.of] " + format_language(lang, na), file=sys.stderr)
        return lang

    @classmethod
    def of_ltl(cls, f: Union[str, "spot.formula"]) -> "Language":
        """A Language from an LTL/PSL formula (string or spot.formula). The formula is
        translated to an automaton lazily on the first representation request.
        Interned on the canonical formula string.

        When `f` is syntactically LTL, the language is LTL-definable BY CONSTRUCTION
        (we hold a defining formula), so the verdict is recorded as a proof —
        `(definable=True, conclusive=True)` — sparing the kr aperiodicity oracle. A
        PSL/SERE `f` is left undecided: its language may lie outside LTL, so the
        oracle must still rule.

        The intern key is the DAG-structural fingerprint `dag_md5(f)`, NOT `str(f)`:
        flattening a hash-consed formula is O(unfolded tree) — exponential on a shared
        DAG (a re-presented operand can have a tiny DAG but a multi-MB flat string), so
        keying on the flat string blows the bank just to make a cache key. `str` /
        flatten is print-only and size-gated (`ltl/printers.format_gated`); identity is
        the O(DAG) `dag_md5` (the full 32-hex digest — a key collision would mis-identify
        a language, so we do NOT truncate to the cosmetic `MD5_LENGTH`)."""
        from aut2ltl.ltl.printers import dag_md5      # deferred: keep the floor import-acyclic
        if isinstance(f, str):
            f = spot.formula(f)
        key = "L\n" + dag_md5(f, 32)

        def build() -> "Language":
            lang = cls(formula=f, lid=_fingerprint(key))
            if f.is_ltl_formula():                    # LTL ⇒ definable, by construction
                lang.set_ltl_definable(True, conclusive=True)
            return lang

        if _OF_TRACE:
            print(f"[language.of_ltl] f={f} -> id={_fingerprint(key)}", file=sys.stderr)
        return _intern(key, build)

    # --- base automaton (source as given, or the formula translated) ---

    def _base(self) -> "spot.twa_graph":
        """The source automaton — the HOA as given, or `formula.translate()` —
        after a language-preserving `_clean` (state purge, redundant-acc-set merge,
        unused-AP drop). Cleaned once, lazily, then cached. The formula is
        translated via `spotrun.translate`, which guards an over-budget formula
        (raising `UntranslatableLanguage`) rather than blowing ltl2tgba up."""
        a = self._cache.get("base")
        if a is None:
            if self._source_aut is not None:
                raw = self._source_aut
            else:
                raw = (self._translate_traced(self._source_formula) if _TRACE
                       else spotrun.translate(self._source_formula))
            from aut2ltl.ltl import canon  # EXPERIMENT: canonicalize the base numbering
            a = canon.normalize(_clean(raw))
            self._cache["base"] = a
        return a

    def _translate_traced(self, f: "spot.formula") -> "spot.twa_graph":
        """`spotrun.translate(f)` timed for `AUT2LTL_LANG_TRACE`: one stderr line
        with the wall time, the input formula's DAG sizes (O(DAG) — never a flatten),
        and the resulting automaton's size. The reporting line, not the construction.
        Routes through the seam so the size guard covers the traced path too."""
        from aut2ltl.ltl.metrics import dag_node_count, temporal_node_count
        from aut2ltl.ltl.printers import dag_md5
        t0 = time.monotonic()
        aut = spotrun.translate(f)
        wall = time.monotonic() - t0
        print(f"[lang.translate] dag={dag_node_count(f)} temporal={temporal_node_count(f)} "
              f"wall={wall:.3f}s -> states={aut.num_states()} edges={aut.num_edges()} "
              f"id={dag_md5(f)}", file=sys.stderr, flush=True)
        return aut

    # --- representations (lazy + cached, named by representation) ---

    def tgba(self) -> "spot.twa_graph":
        """A (generalized) Büchi automaton, NOT forced deterministic — the
        nondeterministic translate-style form the heuristic/sl engine exploits."""
        a = self._cache.get("tgba")
        if a is None:
            from aut2ltl.ltl import canon
            a = canon.normalize(spot.postprocess(self._base(), "tgba"))
            self._cache["tgba"] = a
        return a

    def det_parity_sbacc(self) -> "spot.twa_graph":
        """Deterministic, complete, min-even parity with STATE-BASED acceptance —
        the input form the Krohn-Rhodes cascade is built from (bls/aut2cas.py).
        State-based acceptance is the cascade's soundness requirement (the lifted
        Muller condition is over configurations/states)."""
        a = self._cache.get("det_parity_sbacc")
        if a is None:
            from aut2ltl.ltl import canon
            a = canon.normalize(spot.postprocess(self._base(), "parity min even",
                                                 "deterministic", "complete", "sbacc"))
            self._cache["det_parity_sbacc"] = a
        return a

    def det_generic(self) -> "spot.twa_graph":
        """Deterministic automaton in GENERIC (natural) acceptance — the form on
        which coBüchi/weak recognizability is read (the parity step can hide it)."""
        a = self._cache.get("det_generic")
        if a is None:
            from aut2ltl.ltl import canon
            a = canon.normalize(spot.postprocess(self._base(), "deterministic", "generic"))
            self._cache["det_generic"] = a
        return a

    def det_generic_minimal(self) -> "spot.twa_graph":
        """`det_generic()` further STATE-minimized (SAT, gated to small automata) —
        the form the AND/strength decomposition needs. Best-effort: falls back to
        `det_generic()` on a large or unsolved automaton."""
        a = self._cache.get("det_generic_minimal")
        if a is None:
            from aut2ltl.ltl import canon
            det = self.det_generic()
            if det.num_states() <= _SAT_MIN_STATES:
                try:
                    m = spot.sat_minimize(det)
                    if m is not None and m.num_states() < det.num_states():
                        det = canon.normalize(m)   # re-canonicalize: sat_minimize renumbers
                except Exception:
                    pass
            self._cache["det_generic_minimal"] = det
            a = det
        return a

    @property
    def id(self) -> Optional[str]:
        """Short fingerprint of the intern key — the same re-presented language
        shares it across the run. Stamped by `of`/`of_ltl`; never triggers a build."""
        return self._id

    # --- LTL-definability tag (a property of the language; SET by the kr tester,
    #     not derived here — the GAP aperiodicity oracle lives above this floor) ---

    @property
    def ltl_definable(self) -> Optional[Tuple[Optional[bool], bool]]:
        """The cached LTL-definability reading as `(definable, conclusive)`, or
        `None` if not yet decided. `definable` is True iff an LTL formula exists
        for this language (the transition monoid of a deterministic form is
        aperiodic — a proof), False iff that monoid carries a group (a suspicion,
        not a proof — see the definability package), and None when the oracle
        could not run at all (extraction/GAP failure): unable to certify either
        way. `conclusive` records whether the form was genuinely state-minimal.
        Filled by the kr LtlTester via `set_ltl_definable`; Language never
        computes it itself (that would invert the floor -> kr layering)."""
        return self._ltl_definable

    def set_ltl_definable(self, definable: Optional[bool], *, conclusive: bool) -> None:
        """Record the LTL-definability reading for this language (idempotent
        memo; `definable=None` = the oracle could not run). Called by the kr
        LtlTester after the aperiodicity oracle runs."""
        self._ltl_definable = (definable, conclusive)


__all__ = ["Language"]
