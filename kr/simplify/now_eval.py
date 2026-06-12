"""
now_eval.py — Rule 2: one-step temporal unrolling under boolean context.

A boolean conjunct A in `A ∧ φ` is knowledge about the evaluation instant
of φ — an "initial state" for that subformula, however deeply nested the
And is (LTL adaptation of LogicSimplifier.evalInInitial, after Bonneland
et al., PetriNets 2018). Each temporal operator is unrolled once at that
instant; only SHRINKING rewrites are applied:

    G f          ctx ⊨ ¬f          → false        (G f ≡ f ∧ XG f)
    F f          ctx ⊨ f           → true         (F f ≡ f ∨ XF f)
    f U g, f W g ctx ⊨ g           → true         (≡ g ∨ (f ∧ X·))
                 ctx ⊨ ¬f ∧ ¬g     → false
                 ctx ⊨ ¬f          → g
    f R g, f M g ctx ⊨ ¬g          → false        (≡ g ∧ (f ∨ X·))
                 ctx ⊨ f ∧ g       → true
                 ctx ⊨ f           → g
    X ·          never touched (knowledge is about NOW)

Entailment ctx ⊨ x is two-tier:
  - identity: x ∈ pos (resp. its negation via neg) — works for temporal
    arms too, courtesy of hash-consing;
  - propositional: BDD implication of the propositional fragment of the
    context against a propositional x (own process-lifetime bdd_dict —
    no kr/ dependencies; spot's dict aborts at exit if vars stay
    registered, hence dict+owner live for the process).

The returned right arm `g` is at the SAME instant, so the caller may keep
simplifying it under the same context.
"""

from __future__ import annotations
from typing import FrozenSet, Optional

import buddy
import spot

_bdd_dict = None
_bdd_owner = None


def use_bdd_dict(d, owner) -> None:
    """Inject a shared bdd_dict + owner (pipeline use). Running a second
    dict next to the construction's own corrupted the heap in the equiv
    children (free(): invalid pointer on F(a&Xb)); sharing one dict per
    process avoids it. Standalone use keeps the lazily-created own dict."""
    global _bdd_dict, _bdd_owner
    _bdd_dict, _bdd_owner = d, owner


def _prop_bdd(f: "spot.formula"):
    """BDD of a purely-boolean formula, or None."""
    global _bdd_dict, _bdd_owner
    if not f.is_boolean():
        return None
    if _bdd_dict is None:
        _bdd_dict = spot.make_bdd_dict()
        _bdd_owner = spot.make_twa_graph(_bdd_dict)
    try:
        return spot.formula_to_bdd(f, _bdd_dict, _bdd_owner)
    except Exception:
        return None


def _ctx_bdd(pos: FrozenSet, neg: FrozenSet):
    """Conjunction of the propositional members of the context (buddy bdd)."""
    ctx = buddy.bddtrue
    for f in pos:
        b = _prop_bdd(f)
        if b is not None:
            ctx = buddy.bdd_and(ctx, b)
    for f in neg:
        b = _prop_bdd(f)
        if b is not None:
            ctx = buddy.bdd_and(ctx, buddy.bdd_not(b))
    return ctx


def _entails(ctx, pos: FrozenSet, neg: FrozenSet, x: "spot.formula") -> bool:
    """ctx ⊨ x (sound, incomplete): identity first, then BDD implication."""
    if x in pos:
        return True
    if x._is(spot.op_Not) and x[0] in neg:
        return True
    bx = _prop_bdd(x)
    if bx is None:
        return False
    return buddy.bdd_and(ctx, buddy.bdd_not(bx)) == buddy.bddfalse


def _entails_not(ctx, pos: FrozenSet, neg: FrozenSet, x: "spot.formula") -> bool:
    """ctx ⊨ ¬x."""
    if x in neg:
        return True
    if x._is(spot.op_Not) and x[0] in pos:
        return True
    bx = _prop_bdd(x)
    if bx is None:
        return False
    return buddy.bdd_and(ctx, bx) == buddy.bddfalse


def prop_minimize(f: "spot.formula") -> Optional["spot.formula"]:
    """Minato-ISOP minimal form of a purely-propositional formula via the
    BDD round-trip, or None when f isn't propositional / the round-trip
    fails. Shares the module's process-lifetime bdd_dict."""
    b = _prop_bdd(f)
    if b is None:
        return None
    try:
        return spot.bdd_to_formula(b, _bdd_dict)
    except Exception:
        return None


def now_rewrite(node: "spot.formula", pos: FrozenSet, neg: FrozenSet) -> Optional["spot.formula"]:
    """One shrinking rewrite of a temporal head under the context, or None.
    The result is at the same instant as `node` (same context applies)."""
    if not (pos or neg):
        return None
    ctx = _ctx_bdd(pos, neg)

    if node._is(spot.op_G):
        if _entails_not(ctx, pos, neg, node[0]):
            return spot.formula.ff()
        return None
    if node._is(spot.op_F):
        if _entails(ctx, pos, neg, node[0]):
            return spot.formula.tt()
        return None
    if node._is(spot.op_U) or node._is(spot.op_W):
        f, g = node[0], node[1]
        if _entails(ctx, pos, neg, g):
            return spot.formula.tt()
        if _entails_not(ctx, pos, neg, f):
            if _entails_not(ctx, pos, neg, g):
                return spot.formula.ff()
            return g
        return None
    if node._is(spot.op_R) or node._is(spot.op_M):
        f, g = node[0], node[1]
        if _entails_not(ctx, pos, neg, g):
            return spot.formula.ff()
        if _entails(ctx, pos, neg, f):
            if _entails(ctx, pos, neg, g):
                return spot.formula.tt()
            return g
        return None
    return None
