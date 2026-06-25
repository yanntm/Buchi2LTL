"""aut2ltl.spotrun — the single seam for formula -> automaton translation.

`translate` is the one place the construction turns a formula into an automaton,
so the policy for how that heavy Spot call runs lives here rather than inlined at
the call site (see README.md). It guards the formula against a size budget, then
translates under a wall-time budget: by default (3s) as a killable `ltl2tgba`
child so one runaway node degrades that node, not the whole build; with the
budget disabled (0), via the in-process binding.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

import spot

from aut2ltl import bounded
from aut2ltl.options import OptionSpec

# The bounded-translate child (runs the binding, not the ltl2tgba CLI — see _child.py).
_CHILD = os.path.join(os.path.dirname(__file__), "_child.py")

__all__ = ["translate", "TRANSLATE_TREE_LIMIT", "TRANSLATE_TEMPORAL_LIMIT",
           "TRANSLATE_TIMEOUT", "INPROC_TREE_LIMIT", "INPROC_TEMPORAL_LIMIT",
           "SPOTRUN_OPTIONS"]

# Bound on what we hand ltl2tgba (`f.translate()` below). Spot's translate has no
# graceful failure on an exponentially large formula — it blows up — so we refuse
# one whose unfolded (flat) size or temporal-operator count is over budget,
# raising `UntranslatableLanguage` BEFORE the call. Only a re-presentation (the
# round trip) ever feeds a formula this large here; real inputs are tiny and never
# trip it. 0 disables a bound. (Bucket 3, like SAT_MIN_STATES: a process-wide gate,
# env-read; the OptionSpec is discoverability.)
_TRANSLATE_TREE_LIMIT = int(os.environ.get("KR_TRANSLATE_TREE_LIMIT", "1000"))
_TRANSLATE_TEMPORAL_LIMIT = int(os.environ.get("KR_TRANSLATE_TEMPORAL_LIMIT", "32"))

# Wall-time budget per ltl2tgba translate. Always on (default 3s): a formula that
# passes the size guard yet still translates slowly (translate is exp in formula
# size) is run as a killable ltl2tgba child and declined on overrun, so one runaway
# node degrades that node — which `best_of` absorbs — not the whole build. The
# in-process binding cannot be interrupted (GIL), so a real bound needs the child;
# 0 disables it and reverts to the binding. Bucket 3 (env-read; the OptionSpec is
# discoverability).
_TRANSLATE_TIMEOUT = int(os.environ.get("KR_TRANSLATE_TIMEOUT", "3"))

# Fast path: a formula at or below this (small) size translates in-process,
# unbounded — the binding is instant on small formulas and matches the
# reconstruction exactly, so a subprocess fork would be pure overhead. We trade the
# strict wall-time guarantee for these (a small formula does not blow up; translate
# is exp in size), keeping the bound for the larger formulas that actually risk
# hanging. Either limit <= 0 disables the fast path (force the bounded child).
_INPROC_TREE_LIMIT = int(os.environ.get("KR_TRANSLATE_INPROC_TREE_LIMIT", "100"))
_INPROC_TEMPORAL_LIMIT = int(os.environ.get("KR_TRANSLATE_INPROC_TEMPORAL_LIMIT", "16"))

TRANSLATE_TREE_LIMIT = OptionSpec(
    "spotrun.translate_tree_limit", 1000,
    "refuse ltl2tgba on a formula whose unfolded (flat) size exceeds this; 0 disables",
    env="KR_TRANSLATE_TREE_LIMIT")
TRANSLATE_TEMPORAL_LIMIT = OptionSpec(
    "spotrun.translate_temporal_limit", 32,
    "refuse ltl2tgba on a formula whose temporal-operator count exceeds this; 0 disables",
    env="KR_TRANSLATE_TEMPORAL_LIMIT")
TRANSLATE_TIMEOUT = OptionSpec(
    "spotrun.translate_timeout", 3,
    "wall-seconds budget per ltl2tgba translate, killed on overrun (-> decline); "
    "0 = the in-process binding, unbounded",
    env="KR_TRANSLATE_TIMEOUT")
INPROC_TREE_LIMIT = OptionSpec(
    "spotrun.inproc_tree_limit", 100,
    "translate in-process (unbounded, fast) when flat size <= this; above it, the "
    "bounded ltl2tgba child. <=0 disables the fast path",
    env="KR_TRANSLATE_INPROC_TREE_LIMIT")
INPROC_TEMPORAL_LIMIT = OptionSpec(
    "spotrun.inproc_temporal_limit", 16,
    "translate in-process (unbounded, fast) when temporal-operator count <= this. "
    "<=0 disables the fast path",
    env="KR_TRANSLATE_INPROC_TEMPORAL_LIMIT")

SPOTRUN_OPTIONS = [TRANSLATE_TREE_LIMIT, TRANSLATE_TEMPORAL_LIMIT, TRANSLATE_TIMEOUT,
                   INPROC_TREE_LIMIT, INPROC_TEMPORAL_LIMIT]


def _guard_translation(f: "spot.formula") -> None:
    """Refuse to hand ltl2tgba a formula too large to translate safely — raise
    `UntranslatableLanguage` BEFORE the call. The temporal-operator count walks the
    DAG (cheap); the unfolded (flat) size is measured with a CAP so we never unfold
    an exp tree merely to reject it — `tree_node_count` SATURATES at its `limit`, so
    we cap at limit+1 and test `> limit` to catch strict overflow. 0 disables a
    bound. The imports are deferred to keep this floor import-acyclic
    (`UntranslatableLanguage` is a property of `Language`, which imports spotrun)."""
    from aut2ltl.ltl.metrics import temporal_node_count, tree_node_count
    from aut2ltl.language import UntranslatableLanguage
    if _TRANSLATE_TEMPORAL_LIMIT and temporal_node_count(f) > _TRANSLATE_TEMPORAL_LIMIT:
        raise UntranslatableLanguage(
            f"temporal-operator count over budget (> {_TRANSLATE_TEMPORAL_LIMIT})")
    if _TRANSLATE_TREE_LIMIT and \
            tree_node_count(f, limit=_TRANSLATE_TREE_LIMIT + 1) > _TRANSLATE_TREE_LIMIT:
        raise UntranslatableLanguage(
            f"unfolded (flat) size over budget (> {_TRANSLATE_TREE_LIMIT})")


def _within_inproc(f: "spot.formula") -> bool:
    """True when `f` is small enough to translate in-process unbounded — the fork is
    not worth it and the binding matches the reconstruction exactly. Both bounds must
    hold; either limit <= 0 disables the fast path (force the bounded child)."""
    if _INPROC_TREE_LIMIT <= 0 or _INPROC_TEMPORAL_LIMIT <= 0:
        return False
    from aut2ltl.ltl.metrics import temporal_node_count, tree_node_count
    return (temporal_node_count(f) <= _INPROC_TEMPORAL_LIMIT
            and tree_node_count(f, limit=_INPROC_TREE_LIMIT + 1) <= _INPROC_TREE_LIMIT)


def translate(f: "spot.formula", *, timeout: Optional[int] = None) -> "spot.twa_graph":
    """Translate `f` to an automaton — the single mediated Spot translate.

    Guards `f` against the size budget (`_guard_translation`, raising
    `UntranslatableLanguage` if over). Then the backend: a SMALL formula (within the
    `spotrun.inproc_*` thresholds) or a non-positive budget runs the in-process
    binding (`f.translate()`) unbounded — instant and reconstruction-exact. A larger
    formula under a positive `timeout` (None -> `spotrun.translate_timeout`) runs as
    a killable `ltl2tgba` child, raising `UntranslatableLanguage` on overrun/failure.

    Soundness rests on equivalence, not identity: the child and the binding
    translate the SAME formula, and `language._base` re-cleans the result."""
    _guard_translation(f)
    eff = _TRANSLATE_TIMEOUT if timeout is None else timeout
    if not eff or eff <= 0 or _within_inproc(f):
        if os.environ.get("KR_SPOTRUN_REPARSE"):      # debug: reparse str(f) in-process
            return spot.formula(str(f)).translate()
        a = f.translate()
        if os.environ.get("KR_SPOTRUN_INPROC_RT"):    # debug: in-process HOA round-trip
            a = spot.automaton(a.to_str("hoa"))
        return a
    # Safe to flatten: the size guard proved the unfolded form is <= the tree limit,
    # so `str(f)` is a small string; the exp work (the translate) runs in the child.
    res = bounded.run([sys.executable, _CHILD, str(f)], timeout=eff)
    from aut2ltl.language import UntranslatableLanguage
    # Decline on any child-side failure: overrun, or a non-zero exit (spot raised on
    # the translate, or the formula failed to reparse). The child reports the cause
    # on stderr, so surface a snippet of it for diagnosis.
    if res.timed_out or res.rc not in (0,):
        raise UntranslatableLanguage(
            f"bounded translate over {eff}s budget or failed "
            f"(timed_out={res.timed_out}, rc={res.rc}): {(res.err or '').strip()[:200]}")
    # rc 0 but stdout need not be a parseable automaton (truncated/empty on a crash
    # that still exits 0); a parse failure raises a non-UntranslatableLanguage
    # exception that would escape the seam — convert it to the per-node decline.
    try:
        aut = spot.automaton(res.out)
    except Exception as exc:
        raise UntranslatableLanguage(
            f"bounded-translate output not parseable as an automaton: {exc}") from exc
    if os.environ.get("KR_SPOTRUN_CMP"):
        _debug_compare(f, aut)
    return aut


def _debug_compare(f: "spot.formula", child: "spot.twa_graph") -> None:
    """Temporary instrument (KR_SPOTRUN_CMP): for the SAME formula, compare the plain
    binding vs the reparse-of-str(f) binding — is the difference a pure state
    permutation (isomorphic), and did str(f) round-trip change the formula?"""
    ref = f.translate()                                # good order (reconstructs small)
    if ref.to_str("hoa") == child.to_str("hoa"):
        return
    n = getattr(_debug_compare, "_n", 0)               # dump divergent node pairs
    if n < 8:
        os.makedirs("logs/nodes", exist_ok=True)
        with open(f"logs/nodes/good_{n}.hoa", "w") as fh:
            fh.write(ref.to_str("hoa"))
        with open(f"logs/nodes/perm_{n}.hoa", "w") as fh:
            fh.write(child.to_str("hoa"))
        _debug_compare._n = n + 1
        sys.stderr.write(f"[cmp] DIFFER#{n} ref={ref.num_states()}st child={child.num_states()}st\n")
        sys.stderr.flush()
