"""
kr/simplify — generic LTL simplification rules over spot.formula DAGs.

Independent of the kr/ decomposition; see README.md for the rule catalog,
lineage and soundness notes.
"""

import os as _os

from . import context_pass as _cp
from . import factor_pass as _fp
from . import fold_pass as _dp
from . import now_eval
from .context_pass import context_simplify
from .now_eval import now_rewrite, prop_minimize
from .factor_pass import factor_simplify
from .fold_pass import fold_simplify

_node_memo: dict = {}

# Factoring can INCREASE the number of distinct temporal subformulas
# (variant forms coexist across branches) — locally smaller trees, more
# eventualities, which is the Couvreur acc-set driver. KR_SIMP_OWN_FACTOR=0
# runs the pipeline with rules 1+2 only.
_OWN_FACTOR = _os.getenv("KR_SIMP_OWN_FACTOR", "1").lower() not in ("0", "false", "no", "off")

# Folding (rule 4) strictly shrinks AND lowers the distinct-temporal census;
# KR_SIMP_OWN_FOLD=0 restores the rules-1..3 pipeline.
_OWN_FOLD = _os.getenv("KR_SIMP_OWN_FOLD", "1").lower() not in ("0", "false", "no", "off")


def _ctx_simplify(f: "spot.formula") -> "spot.formula":
    """Context pass with both hooks: now-evaluation (rule 2) on temporal
    heads, context-aware S1/S2 subsumption (fold_pass.ctx_subsume) on
    boolean nodes — the initial-state knowledge applied at both levels."""
    return context_simplify(f, now_hook=now_rewrite,
                            bool_hook=_dp.ctx_subsume)


def simplify(f: "spot.formula") -> "spot.formula":
    """Combined pipeline: context pass (rule 1) with the now-evaluation
    hook (rule 2), then unroll-inverse folding (rule 4, unless
    KR_SIMP_OWN_FOLD=0), then partial factoring (rule 3, unless
    KR_SIMP_OWN_FACTOR=0); a pass that changed something is followed by
    one more context pass (composites can expose new absorptions) and,
    after factoring, one more fold (factoring can expose fold partners).
    Language-preserving."""
    _ctx = _ctx_simplify
    g = _ctx(f)
    if _OWN_FOLD:
        h = fold_simplify(g)
        if h != g:
            g = _ctx(h)
    if not _OWN_FACTOR:
        return g
    h = factor_simplify(g)
    if h != g:
        h = _ctx(h)
        if _OWN_FOLD:
            h2 = fold_simplify(h)
            if h2 != h:
                h = _ctx(h2)
    return h


def simplify_node(f: "spot.formula") -> "spot.formula":
    """Per-DAG-node entry for pipeline use (e.g. inside kr's _simp_f):
    memoized fixpoint of `simplify`. All underlying memos are persistent,
    so calling this bottom-up over a DAG is amortized O(1) per node —
    the call count is the DAG size, never the unfolded tree."""
    hit = _node_memo.get(f)
    if hit is not None:
        return hit
    res = simplify(f)
    _node_memo[f] = res
    _node_memo[res] = res  # fixpoint entry
    return res


def reset_caches() -> None:
    """Drop all persistent memos (tests / memory pressure)."""
    _node_memo.clear()
    _cp.reset_cache()
    _fp.reset_cache()
    _dp.reset_cache()


__all__ = ["context_simplify", "now_rewrite", "prop_minimize",
           "factor_simplify", "fold_simplify", "simplify", "simplify_node",
           "reset_caches"]
