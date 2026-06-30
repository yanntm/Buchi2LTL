"""
spot_EU_rules.py — Spot's eventual/universal rewrite rules, the O(DAG) subset.

Source: Spot 2.15.1 documentation §5.4.2 + the implementation in
`spot/tl/simplify.cc` (the `mospliter` event/universal split and the
`simplify_visitor` unary/binary cases). The full rule catalogue — including the
size-increasing and `favor_event_univ`-gated forms — is in `algorithm_EU_rules.md`;
this module implements only the **always-applied (≡)** unary/binary rules, the
ones that never increase size and have no `≡` inverse (so they cannot ping-pong).

Why a separate pass. Spot's own `tl_simplifier` already knows these rules, but it
is NOT O(input-DAG): several of its steps (boolean→BDD→ISOP, containment DNF/CNF,
the regrouping rebuilds) materialise off-DAG nodes whose count is not bounded by
the input, so it can explode a small DAG into a 10^10-node tree. The three class
tests it keys on, by contrast, ARE O(1): `is_eventual()` / `is_universal()` are
cached node bits on Spot's hash-consed DAG (a bottom-up boolean recurrence over the
children's bits). Reading them straight off the node and rewriting locally keeps
this pass strictly O(DAG): one memoised bottom-up walk, each rule strips or
relocates one operator, never adding a node.

The classes (sound-but-incomplete syntactic predicates — every guarded rule is a
true equivalence wherever it fires; we only miss unflagged opportunities):

    e  pure eventuality   F e ≡ e        f.is_eventual()
    u  purely universal   G u ≡ u        f.is_universal()
    q  suspendable        both           is_eventual() and is_universal()

Rules (a = left child, b = right child):

    F e            ≡ e
    G u            ≡ u
    X q            ≡ q
    f U e          ≡ e
    f R u          ≡ u
    u W g          ≡ u ∨ g
    e M g          ≡ e ∧ g
    q U X g        ≡ X(q U g)
    q R X g        ≡ X(q R g)

The pass is standalone (own memo + reset_cache, entry `eu_simplify`). It is NOT
wired into the default pipeline yet: the n-ary lifting/distribution blocks of
`algorithm_EU_rules.md` overlap our own `fold_pass` (GF/FG cofactoring) and must be
reconciled first.
"""

from __future__ import annotations
from typing import Dict

import spot


def _suspendable(f: "spot.formula") -> bool:
    """q: both a pure eventuality and purely universal (Spot's 'suspendable')."""
    return f.is_eventual() and f.is_universal()


def _eu_node(n: "spot.formula") -> "spot.formula":
    """Apply the always-applied (≡) eventual/universal rules to a single temporal
    node whose children are already simplified, repeatedly until none fires. Each
    rule strips or relocates exactly one operator (no node added), so the loop
    converges; there is no ≡ inverse among them, so it cannot ping-pong."""
    while True:
        if n._is(spot.op_F):                       # F e ≡ e
            if n[0].is_eventual():
                n = n[0]; continue
        elif n._is(spot.op_G):                     # G u ≡ u
            if n[0].is_universal():
                n = n[0]; continue
        elif n._is(spot.op_X):                     # X q ≡ q
            if _suspendable(n[0]):
                n = n[0]; continue
        elif n._is(spot.op_U):
            a, b = n[0], n[1]
            if b.is_eventual():                    # f U e ≡ e
                n = b; continue
            if _suspendable(a) and b._is(spot.op_X):   # q U X g ≡ X(q U g)
                n = spot.formula.X(spot.formula.U(a, b[0])); continue
        elif n._is(spot.op_R):
            a, b = n[0], n[1]
            if b.is_universal():                   # f R u ≡ u
                n = b; continue
            if _suspendable(a) and b._is(spot.op_X):   # q R X g ≡ X(q R g)
                n = spot.formula.X(spot.formula.R(a, b[0])); continue
        elif n._is(spot.op_W):                     # u W g ≡ u ∨ g
            a, b = n[0], n[1]
            if a.is_universal():
                n = spot.formula.Or([a, b]); continue
        elif n._is(spot.op_M):                     # e M g ≡ e ∧ g
            a, b = n[0], n[1]
            if a.is_eventual():
                n = spot.formula.And([a, b]); continue
        return n


_memo: Dict["spot.formula", "spot.formula"] = {}


def reset_cache() -> None:
    """Drop the persistent memo (tests / memory pressure)."""
    _memo.clear()


def eu_simplify(f: "spot.formula") -> "spot.formula":
    """Bottom-up application of the always-applied eventual/universal rules over
    the whole DAG (memoised). O(DAG): each node is visited once, the per-node work
    reads cached class bits and rebuilds at most one operator."""
    memo = _memo

    def walk(n: "spot.formula") -> "spot.formula":
        hit = memo.get(n)
        if hit is not None:
            return hit
        if list(n):                       # any node with children: rebuild then rule
            out = n.map(walk)
            # And/Or carry no ≡ EU rule here (the n-ary blocks are deferred); only
            # temporal nodes are rewritten, on already-simplified children.
            if not (out._is(spot.op_And) or out._is(spot.op_Or)):
                out = _eu_node(out)
        else:
            out = n
        memo[n] = out
        return out

    return walk(f)


__all__ = ["eu_simplify", "reset_cache"]
