"""
context_pass.py — Rule 1: context-carrying boolean-skeleton simplification.

Adapts the seenPos/seenNeg/dominant mechanics of the user's Java
`Simplifier.simplifyBoolean` to spot.formula DAGs (see kr/simplify/README.md
for the rule statement and soundness note).

Core ideas:
- Walk the And/Or skeleton top-down carrying (pos, neg) frozensets of
  asserted subformulas; any node found in a set rewrites to tt/ff
  (identity-based domination — temporal nodes included).
- At And, sibling atoms are asserted true for each child; at Or, asserted
  false (Shannon). "Atom" = any non-And/Or child.
- Context resets to empty at every non-boolean operator (knowledge about
  "now" never crosses X/U/G/F/R/W/M); bodies are still visited so nested
  skeletons simplify everywhere.
- Hash-consing makes set membership identity-based and the empty-context
  bulk memoizable per node: O(DAG) outside the skeleton.

No kr/ dependencies: generic LTL in, generic LTL out.
"""

from __future__ import annotations
from typing import Dict, FrozenSet, Tuple

import spot

_EMPTY: FrozenSet["spot.formula"] = frozenset()

# Persistent memo (formulas are immutable hash-consed objects, so caching
# across calls is safe). Key includes whether a now-hook is active — the
# fixpoints differ. Persistence is what makes per-DAG-node pipeline usage
# (kr.simplify.simplify_node inside _simp_f) amortized O(1) per node:
# children of a fresh node are already memoized fixpoints.
_memo: Dict[Tuple, "spot.formula"] = {}


def reset_cache() -> None:
    _memo.clear()


def _is_bool_node(f: "spot.formula") -> bool:
    return f._is(spot.op_And) or f._is(spot.op_Or)


def _const_fold(f: "spot.formula") -> "spot.formula":
    """Trivial constant folds through unary temporal heads after a body
    rewrite (X(0)→0, G(1)→1, F(0)→0, …). Anything richer is delegated to
    Spot's basics downstream."""
    if f._is(spot.op_X) or f._is(spot.op_F) or f._is(spot.op_G):
        c = f[0]
        if c.is_tt() or c.is_ff():
            return c
    return f


def context_simplify(f: "spot.formula", now_hook=None) -> "spot.formula":
    """Simplify f using sibling-context propagation over the boolean
    skeleton. Returns a formula language-equivalent to f.

    `now_hook(node, pos, neg) -> formula | None` (rule 2, now_eval) is
    tried on every non-boolean node sitting under a non-empty context,
    BEFORE the boundary reset; a non-None replacement is at the same
    instant, so it keeps simplifying under the same context."""
    memo = _memo
    hooked = now_hook is not None

    def walk(node: "spot.formula", pos: FrozenSet, neg: FrozenSet) -> "spot.formula":
        # 1. domination by identity (any node kind, temporal included)
        if node in pos:
            return spot.formula.tt()
        if node in neg:
            return spot.formula.ff()
        if node._is(spot.op_Not):
            child = node[0]
            if child in pos:
                return spot.formula.ff()
            if child in neg:
                return spot.formula.tt()
        if node.is_tt() or node.is_ff() or node._is(spot.op_ap):
            return node

        key = (hooked, node, pos, neg)
        hit = memo.get(key)
        if hit is not None:
            return hit

        if _is_bool_node(node):
            is_and = node._is(spot.op_And)
            kids = list(node)
            # Sibling atoms: anything that is not And/Or is opaque ("now"
            # assertion at And / refutation at Or). Not(x) contributes x to
            # the dual set.
            atoms = [k for k in kids if not _is_bool_node(k)]
            res_kids = []
            for k in kids:
                others = [o for o in atoms if o is not k]
                add_direct = {o for o in others if not o._is(spot.op_Not)}
                add_dual = {o[0] for o in others if o._is(spot.op_Not)}
                if is_and:
                    np_, nn_ = pos | add_direct, neg | add_dual
                else:
                    np_, nn_ = pos | add_dual, neg | add_direct
                res_kids.append(walk(k, frozenset(np_), frozenset(nn_)))
            out = spot.formula.And(res_kids) if is_and else spot.formula.Or(res_kids)
            # The constructors fold constants / dedupe / flatten; if that
            # exposed new atom siblings, one more pass picks them up.
            # NB: structural !=, not `is not` — spot wrappers are fresh
            # objects even for hash-consed identical formulas.
            if out != node and _is_bool_node(out):
                out = walk(out, pos, neg)
        else:
            # Rule-2 hook: one-step unrolling of the temporal head under
            # the context (same-instant replacement keeps the context).
            if now_hook is not None and (pos or neg):
                rep = now_hook(node, pos, neg)
                if rep is not None and rep != node:
                    out = walk(rep, pos, neg)
                    memo[key] = out
                    return out
            # Non-boolean operator: context boundary. Visit bodies with an
            # empty context, memoized on the node alone (the common case).
            ekey = (hooked, node, _EMPTY, _EMPTY)
            out = memo.get(ekey)
            if out is None:
                out = _const_fold(node.map(lambda c: walk(c, _EMPTY, _EMPTY)))
                memo[ekey] = out

        memo[key] = out
        return out

    return walk(f, _EMPTY, _EMPTY)
