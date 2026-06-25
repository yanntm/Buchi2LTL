"""aut2ltl.spotrun — the single seam for formula -> automaton translation.

`translate` is the one place the construction turns a formula into an automaton,
so the policy for how that heavy Spot call runs lives here rather than inlined at
the call site (see README.md). Today it guards the formula against a size budget,
then translates in-process; the wall-time-bounded `ltl2tgba` backend layers on
next without changing this contract.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from aut2ltl.options import OptionSpec

if TYPE_CHECKING:
    import spot

__all__ = ["translate", "TRANSLATE_TREE_LIMIT", "TRANSLATE_TEMPORAL_LIMIT",
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

TRANSLATE_TREE_LIMIT = OptionSpec(
    "spotrun.translate_tree_limit", 1000,
    "refuse ltl2tgba on a formula whose unfolded (flat) size exceeds this; 0 disables",
    env="KR_TRANSLATE_TREE_LIMIT")
TRANSLATE_TEMPORAL_LIMIT = OptionSpec(
    "spotrun.translate_temporal_limit", 32,
    "refuse ltl2tgba on a formula whose temporal-operator count exceeds this; 0 disables",
    env="KR_TRANSLATE_TEMPORAL_LIMIT")

SPOTRUN_OPTIONS = [TRANSLATE_TREE_LIMIT, TRANSLATE_TEMPORAL_LIMIT]


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


def translate(f: "spot.formula") -> "spot.twa_graph":
    """Translate `f` to an automaton — the single mediated Spot translate.

    Guards `f` against the size budget (`_guard_translation`, raising
    `UntranslatableLanguage` if over) and, when within budget, translates via the
    in-process binding (`f.translate()`). The killable wall-time bound layers on
    later without changing this signature."""
    _guard_translation(f)
    return f.translate()
