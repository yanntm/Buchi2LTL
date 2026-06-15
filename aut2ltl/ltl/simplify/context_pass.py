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
- Temporal siblings are OPENED into now-knowledge instead of staying
  opaque (the initial-state reading of the expansion laws — Gφ ≡ φ ∧ XGφ
  leveraged without materializing the expansion): at And, Gφ asserts the
  conjuncts of φ now, f R g / f M g assert the conjuncts of g now; at Or
  (Shannon: the sibling is assumed FALSE), Fφ refutes each disjunct of φ
  now, f U g / f W g refute the disjuncts of g now (g@0 alone satisfies
  U/W, so ¬(f U g) ⇒ ¬g@0).
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


def _now_facts(o: "spot.formula", is_and: bool):
    """Now-knowledge contributed by a temporal sibling, beyond the sibling
    itself: facts TRUE at this instant when the sibling holds (And side),
    facts TRUE at this instant when the sibling is assumed false (Or side,
    returned as the formulas whose NEGATION is implied)."""
    if is_and:
        body = None
        if o._is(spot.op_G):
            body = o[0]                       # Gφ ⇒ φ now
        elif o._is(spot.op_R) or o._is(spot.op_M):
            body = o[1]                       # f R g / f M g ⇒ g now
        if body is None:
            return ()
        return tuple(body) if body._is(spot.op_And) else (body,)
    body = None
    if o._is(spot.op_F):
        body = o[0]                           # ¬Fφ ⇒ ¬φ now
    elif o._is(spot.op_U) or o._is(spot.op_W):
        body = o[1]                           # g@0 ⇒ f U g, so ¬(f U g) ⇒ ¬g
    if body is None:
        return ()
    return tuple(body) if body._is(spot.op_Or) else (body,)


def _const_fold(f: "spot.formula") -> "spot.formula":
    """Trivial constant folds through unary temporal heads after a body
    rewrite (X(0)→0, G(1)→1, F(0)→0, …). Anything richer is delegated to
    Spot's basics downstream."""
    if f._is(spot.op_X) or f._is(spot.op_F) or f._is(spot.op_G):
        c = f[0]
        if c.is_tt() or c.is_ff():
            return c
    return f


def context_simplify(f: "spot.formula", now_hook=None, bool_hook=None) -> "spot.formula":
    """Simplify f using sibling-context propagation over the boolean
    skeleton. Returns a formula language-equivalent to f.

    `now_hook(node, pos, neg) -> formula | None` (rule 2, now_eval) is
    tried on every non-boolean node sitting under a non-empty context,
    BEFORE the boundary reset; a non-None replacement is at the same
    instant, so it keeps simplifying under the same context.

    `bool_hook(node, pos, neg) -> formula | None` (context-aware
    subsumption, fold_pass.ctx_subsume) is tried on every rebuilt And/Or
    node under a non-empty context; a non-None replacement is re-walked
    under the same context (each application drops a child, so this
    terminates)."""
    memo = _memo
    hooked = (now_hook is not None, bool_hook is not None)

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
            res_kids = []
            for ki, k in enumerate(kids):
                add_pos, add_neg = set(), set()
                for oi, o in enumerate(kids):
                    if oi == ki or _is_bool_node(o):
                        continue
                    # the sibling itself (true at And, false at Or):
                    # bidirectional — support cycles are impossible by DAG
                    # acyclicity (a node cannot be its own subterm).
                    if o._is(spot.op_Not):
                        (add_neg if is_and else add_pos).add(o[0])
                    else:
                        (add_pos if is_and else add_neg).add(o)
                    # opened now-knowledge: ONE-WAY (earlier siblings only).
                    # Two siblings can derive the same fact, so bidirectional
                    # opening builds circular support: in a & b & (a M b) the
                    # derived b erased the sibling b while the M consumed it
                    # (fuzz witness !(b R (Gb & (b M Gb))) -> 0). One-way flow
                    # is sound by sequential replacement: child i is rewritten
                    # in the presence of the ORIGINAL siblings j < i.
                    if oi < ki:
                        for d in _now_facts(o, is_and):
                            if d._is(spot.op_Not):
                                (add_neg if is_and else add_pos).add(d[0])
                            else:
                                (add_pos if is_and else add_neg).add(d)
                res_kids.append(walk(k, frozenset(pos | add_pos),
                                     frozenset(neg | add_neg)))
            out = spot.formula.And(res_kids) if is_and else spot.formula.Or(res_kids)
            if bool_hook is not None and (pos or neg) and _is_bool_node(out):
                rep = bool_hook(out, pos, neg)
                if rep is not None and rep != out:
                    out = rep
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
