"""
fold_pass.py — Rule 4: unroll-inverse folding (the expansion laws, backwards).

The kr/ construction emits temporal obligations in locally-unrolled form
(last-step decomposition, first-occurrence splits): `a | F(!a & Xa)` instead
of `Fa`, `a & G(!a | Xa)` instead of `Ga`, `g | (f & X(f U g))` instead of
`f U g`. Spot's tl_simplifier never folds these back (measured on the
F(a&Xa) dump, kr/testing/logs/faxa_dag_dump.txt). Folding them is the
canonical orientation: every rule below strictly shrinks the tree AND
removes a distinct temporal subformula — the Couvreur acc-set driver.
now_eval only ever returns constants or an arm, so the passes cannot
ping-pong.

At an Or node (dually at And):

    c ∨ X F c               → F c       [F expansion law]
    c ∨ F(¬c ∧ X c)         → F c       [first occurrence: the earliest c
                                         is now or strictly later]
    g ∨ (f ∧ X(f U g))      → f U g     [U expansion law]
    g ∨ (f ∧ X(f W g))      → f W g     [W expansion law]

    c ∧ X G c               → G c       [G expansion law]
    c ∧ G(¬c ∨ X c)         → G c       [induction: c now + G(c → Xc)]
    g ∧ (f ∨ X(f R g))      → f R g     [R expansion law]
    g ∧ (f ∨ X(f M g))      → f M g     [M expansion law]

Plus two sibling-subsumption rules (the Formula-5 line redundancy: the
construction disjoins the strong-reach lines with the "stay forever" G
line, and the G line is implied by the R line whenever the Or also holds
the now-case c):

    c ∨ X(c R d) ∨ G(c ∨ Xd)    → c ∨ X(c R d)     [S1: drop the G]
    c ∧ X(c U d) ∧ F(c ∧ Xd)    → c ∧ X(c U d)     [S2: drop the F, dual]

S1 soundness: assume G(c ∨ Xd) and ¬c now; for any i ≥ 1, either some
j ∈ [1, i-1] has c, or ¬c on [0, i-1] and the G clause at i-1 forces d@i —
exactly c R d from position 1. S2 is the literal dual. The M/W variants are
NOT valid (the c-never case needs no eventual c) and are excluded.

Plus G/F absorption (reading Gφ through its unrolling φ ∧ XGφ): a conjunct
sitting next to Gφ is redundant when Gφ ⇒ it; a disjunct next to Fφ is
redundant when it ⇒ Fφ. Entailment is a small syntactic recursion (sound,
incomplete, memoized on the node pair):

    Gφ ⇒ k   if k ∈ conj(φ) ∪ {φ}; k = Xψ/Fψ/Gψ with Gφ ⇒ ψ;
              k = ψ W χ or χ' R ψ with Gφ ⇒ ψ; And: all; Or: any.
    k ⇒ Fφ   if k ∈ disj(φ) ∪ {φ}; k = Xψ/Fψ/Gψ with ψ ⇒ Fφ;
              k = ψ U χ or ψ M χ with χ ⇒ Fφ; And: any; Or: all.

Each clause is a one-line implication (Gφ holds on every suffix; F is
upward closed under reachability), so absorption only ever DROPS a child.

All rules are plain language equivalences for ARBITRARY c/d/f/g (no
propositional restriction). The ¬c match is two-tier like now_eval:
hash-consed identity against spot.formula.Not(c), then BDD complement for
propositional c. Each fold removes at least one child of the boolean node,
so the per-node loop terminates; the whole pass is a memoized bottom-up
walk, O(DAG) with persistent results.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

import buddy
import spot

from .now_eval import _prop_bdd, _ctx_bdd, _entails, _entails_not


def _is_neg(g: "spot.formula", c: "spot.formula") -> bool:
    """g ≡ ¬c — identity tier (Not constructor folds involution), then BDD
    complement when both sides are propositional."""
    if g == spot.formula.Not(c):
        return True
    bg, bc = _prop_bdd(g), _prop_bdd(c)
    return bg is not None and bc is not None and bg == buddy.bdd_not(bc)


def _find_fold_or(kids: List["spot.formula"]) -> Optional[Tuple[int, int, "spot.formula"]]:
    """One applicable Or-fold: (index, partner index, replacement)."""
    pos = {k: i for i, k in enumerate(kids)}
    for i, k in enumerate(kids):
        # c | XFc -> Fc
        if k._is(spot.op_X) and k[0]._is(spot.op_F):
            j = pos.get(k[0][0])
            if j is not None:
                return i, j, k[0]
        # c | F(¬c & Xc) -> Fc
        if k._is(spot.op_F) and k[0]._is(spot.op_And):
            subs = list(k[0])
            for s in subs:
                if s._is(spot.op_X):
                    j = pos.get(s[0])
                    if j is None:
                        continue
                    rest = spot.formula.And([t for t in subs if t != s])
                    if _is_neg(rest, s[0]):
                        return i, j, spot.formula.F(s[0])
        # g | (f & X(f U g)) -> f U g   (same for W)
        if k._is(spot.op_And):
            subs = list(k)
            for s in subs:
                if s._is(spot.op_X) and (s[0]._is(spot.op_U) or s[0]._is(spot.op_W)):
                    u = s[0]
                    j = pos.get(u[1])
                    if j is None:
                        continue
                    rest = spot.formula.And([t for t in subs if t != s])
                    if rest == u[0]:
                        return i, j, u
    return None


def _find_fold_and(kids: List["spot.formula"]) -> Optional[Tuple[int, int, "spot.formula"]]:
    """One applicable And-fold (dual of _find_fold_or)."""
    pos = {k: i for i, k in enumerate(kids)}
    for i, k in enumerate(kids):
        # c & XGc -> Gc
        if k._is(spot.op_X) and k[0]._is(spot.op_G):
            j = pos.get(k[0][0])
            if j is not None:
                return i, j, k[0]
        # c & G(¬c | Xc) -> Gc
        if k._is(spot.op_G) and k[0]._is(spot.op_Or):
            subs = list(k[0])
            for s in subs:
                if s._is(spot.op_X):
                    j = pos.get(s[0])
                    if j is None:
                        continue
                    rest = spot.formula.Or([t for t in subs if t != s])
                    if _is_neg(rest, s[0]):
                        return i, j, spot.formula.G(s[0])
        # g & (f | X(f R g)) -> f R g   (same for M)
        if k._is(spot.op_Or):
            subs = list(k)
            for s in subs:
                if s._is(spot.op_X) and (s[0]._is(spot.op_R) or s[0]._is(spot.op_M)):
                    r = s[0]
                    j = pos.get(r[1])
                    if j is None:
                        continue
                    rest = spot.formula.Or([t for t in subs if t != s])
                    if rest == r[0]:
                        return i, j, r
    return None


def _find_subsumed_or(kids: List["spot.formula"]) -> Optional[int]:
    """S1: index of a G(c | Xd) disjunct made redundant by sibling
    disjuncts c (possibly split by flattening) and X(c R d)."""
    pos = set(kids)
    for i, k in enumerate(kids):
        if k._is(spot.op_G) and k[0]._is(spot.op_Or):
            body = list(k[0])
            for s in body:
                if s._is(spot.op_X):
                    rest = [t for t in body if t != s]
                    c = spot.formula.Or(rest)
                    if (all(t in pos for t in rest)
                            and spot.formula.X(spot.formula.R(c, s[0])) in pos):
                        return i
    return None


def _find_subsumed_and(kids: List["spot.formula"]) -> Optional[int]:
    """S2 (dual): index of an F(c & Xd) conjunct made redundant by sibling
    conjuncts c and X(c U d)."""
    pos = set(kids)
    for i, k in enumerate(kids):
        if k._is(spot.op_F) and k[0]._is(spot.op_And):
            body = list(k[0])
            for s in body:
                if s._is(spot.op_X):
                    rest = [t for t in body if t != s]
                    c = spot.formula.And(rest)
                    if (all(t in pos for t in rest)
                            and spot.formula.X(spot.formula.U(c, s[0])) in pos):
                        return i
    return None


# Entailment memos, persistent like the pass memo (hash-consed keys).
_g_imp_memo: Dict[Tuple, bool] = {}
_f_imp_memo: Dict[Tuple, bool] = {}


def _g_implies(phi: "spot.formula", conj: frozenset, k: "spot.formula") -> bool:
    """Gφ ⇒ k (sound, incomplete). `conj` = conj(φ) ∪ {φ}."""
    if k == phi or k in conj:
        return True
    key = (phi, k)
    hit = _g_imp_memo.get(key)
    if hit is not None:
        return hit
    res = False
    if k._is(spot.op_X) or k._is(spot.op_F) or k._is(spot.op_G):
        res = _g_implies(phi, conj, k[0])
    elif k._is(spot.op_W):                      # ψ always ⇒ ψ W χ
        res = _g_implies(phi, conj, k[0])
    elif k._is(spot.op_R):                      # ψ always ⇒ χ R ψ
        res = _g_implies(phi, conj, k[1])
    elif k._is(spot.op_And):
        res = all(_g_implies(phi, conj, c) for c in k)
    elif k._is(spot.op_Or):
        res = any(_g_implies(phi, conj, c) for c in k)
    _g_imp_memo[key] = res
    return res


def _implies_f(phi: "spot.formula", disj: frozenset, k: "spot.formula") -> bool:
    """k ⇒ Fφ (sound, incomplete). `disj` = disj(φ) ∪ {φ}."""
    if k == phi or k in disj:
        return True
    key = (phi, k)
    hit = _f_imp_memo.get(key)
    if hit is not None:
        return hit
    res = False
    if k._is(spot.op_X) or k._is(spot.op_F) or k._is(spot.op_G):
        res = _implies_f(phi, disj, k[0])
    elif k._is(spot.op_U) or k._is(spot.op_M):  # both guarantee χ eventually
        res = _implies_f(phi, disj, k[1])
    elif k._is(spot.op_And):
        res = any(_implies_f(phi, disj, c) for c in k)
    elif k._is(spot.op_Or):
        res = all(_implies_f(phi, disj, c) for c in k)
    _f_imp_memo[key] = res
    return res


def _find_absorbed_and(kids: List["spot.formula"]) -> Optional[int]:
    """Index of a conjunct implied by a sibling Gφ (Gφ = φ ∧ XGφ)."""
    for g in kids:
        if g._is(spot.op_G):
            phi = g[0]
            conj = frozenset(list(phi) if phi._is(spot.op_And) else [phi])
            for i, k in enumerate(kids):
                if k != g and _g_implies(phi, conj, k):
                    return i
    return None


def _find_absorbed_or(kids: List["spot.formula"]) -> Optional[int]:
    """Index of a disjunct that implies a sibling Fφ (Fφ = φ ∨ XFφ)."""
    for f in kids:
        if f._is(spot.op_F):
            phi = f[0]
            disj = frozenset(list(phi) if phi._is(spot.op_Or) else [phi])
            for i, k in enumerate(kids):
                if k != f and _implies_f(phi, disj, k):
                    return i
    return None


def _fold_node(node: "spot.formula") -> "spot.formula":
    """Fold one boolean node to its fixpoint (children assumed processed)."""
    is_and = node._is(spot.op_And)
    finder = _find_fold_and if is_and else _find_fold_or
    subsumer = _find_subsumed_and if is_and else _find_subsumed_or
    absorber = _find_absorbed_and if is_and else _find_absorbed_or
    kids = list(node)
    changed = False
    while len(kids) >= 2:
        drop = absorber(kids)
        if drop is None:
            drop = subsumer(kids)
        if drop is not None:
            kids = [k for idx, k in enumerate(kids) if idx != drop]
            changed = True
            continue
        hit = finder(kids)
        if hit is None:
            break
        i, j, rep = hit
        kids = [k for idx, k in enumerate(kids) if idx not in (i, j)]
        kids.append(rep)
        changed = True
    if not changed:
        return node
    return spot.formula.And(kids) if is_and else spot.formula.Or(kids)


def _prop_part_implies(x: "spot.formula", d, conjunctive: bool) -> bool:
    """Sound one-way test using only the propositional fragment of x:
    conjunctive — the BDD AND of x's boolean conjuncts implies d
    (x ⇒ prop(x) ⇒ d); disjunctive — d implies the BDD OR of x's boolean
    disjuncts (d ⇒ prop-disj(x) ⇒ x). d must be propositional."""
    bd = _prop_bdd(d)
    if bd is None:
        return False
    parts = list(x) if (x._is(spot.op_And) if conjunctive else x._is(spot.op_Or)) else [x]
    acc = buddy.bddtrue if conjunctive else buddy.bddfalse
    for t in parts:
        bt = _prop_bdd(t)
        if bt is None:
            continue
        acc = buddy.bdd_and(acc, bt) if conjunctive else buddy.bdd_or(acc, bt)
    if conjunctive:   # acc ⇒ d ?
        return buddy.bdd_and(acc, buddy.bdd_not(bd)) == buddy.bddfalse
    return buddy.bdd_and(bd, buddy.bdd_not(acc)) == buddy.bddfalse


def _arm_unpad(node: "spot.formula") -> "spot.formula":
    """Arm-padding removal (the class-probe pattern, both verified):

        (c ∧ Xd) U g → c U g    when c ⇒ d and g ⇒ d   (same for W)
        (c ∨ Xd) R g → c R g    when d ⇒ c and d ⇒ g

    Soundness (U): before g fires, every next position satisfies c or g,
    both of which imply d — so the Xd conjunct never excludes anything.
    R is the literal dual. Entailments are tested on the propositional
    fragments only (one-way, hence sound); d must be propositional."""
    if node._is(spot.op_U) or node._is(spot.op_W):
        f, g = node[0], node[1]
        if f._is(spot.op_And):
            for s in f:
                if s._is(spot.op_X):
                    rest = [t for t in f if t != s]
                    c = spot.formula.And(rest)
                    if (_prop_part_implies(c, s[0], True)
                            and _prop_part_implies(g, s[0], True)):
                        op = spot.formula.U if node._is(spot.op_U) else spot.formula.W
                        return _arm_unpad(op(c, g))
    elif node._is(spot.op_R):
        f, g = node[0], node[1]
        if f._is(spot.op_Or):
            for s in f:
                if s._is(spot.op_X):
                    rest = [t for t in f if t != s]
                    c = spot.formula.Or(rest)
                    if (_prop_part_implies(c, s[0], False)
                            and _prop_part_implies(g, s[0], False)):
                        return _arm_unpad(spot.formula.R(c, g))
    return node


def ctx_subsume(node: "spot.formula", pos, neg) -> "spot.formula | None":
    """Context-aware S1/S2 (the initial-state reading): under a context
    refuting c, the bare-c disjunct of S1 is discharged by knowledge, so

      X(c R d) ∨ G(c ∨ Xd)                    → X(c R d)         [ctx ⊨ ¬c]
      X(c ∨ X(c R d)) ∨ G(c ∨ X(c ∨ Xd))     → X(c ∨ X(c R d))  [shifted]

    and dually at And under ctx ⊨ c (F conjunct dropped next to the U
    line). Proof of the shifted form: Gβ clause at i-2 plus ¬c on
    [0, i-1] forces d@i for every i ≥ 2 (the i=2 case is exactly where
    ¬c@0 from the context is needed — without it the rule is UNSOUND,
    witness `!a; a; cycle{!a}`). Hooked into the context pass on boolean
    nodes (bool_hook); returns the reduced node or None."""
    is_and = node._is(spot.op_And)
    kids = list(node)
    kidset = set(kids)
    ctx = _ctx_bdd(pos, neg)
    known = (lambda c: _entails(ctx, pos, neg, c)) if is_and \
        else (lambda c: _entails_not(ctx, pos, neg, c))
    wrap_op = spot.formula.U if is_and else spot.formula.R
    bool_op = spot.formula.And if is_and else spot.formula.Or
    head_op, body_op = (spot.op_F, spot.op_And) if is_and else (spot.op_G, spot.op_Or)

    drop = None
    for i, k in enumerate(kids):
        if not (k._is(head_op) and k[0]._is(body_op)):
            continue
        body = list(k[0])
        for s in body:
            if not s._is(spot.op_X):
                continue
            rest = [t for t in body if t != s]
            c = bool_op(rest)
            if not known(c):
                continue
            d = s[0]
            # unshifted: partner X(c R d) / X(c U d)
            if spot.formula.X(wrap_op(c, d)) in kidset:
                drop = i
                break
            # shifted: d = c ∘ Xd2; partner X(c ∘ X(c R/U d2))
            if d._is(body_op):
                inner = list(d)
                for s2 in inner:
                    if s2._is(spot.op_X) and bool_op([t for t in inner if t != s2]) == c:
                        alpha = bool_op(rest + [spot.formula.X(wrap_op(c, s2[0]))])
                        if spot.formula.X(alpha) in kidset:
                            drop = i
                            break
                if drop is not None:
                    break
        if drop is not None:
            break
    if drop is None:
        return None
    rem = [k for j, k in enumerate(kids) if j != drop]
    return bool_op(rem)


# Persistent memo (see context_pass note): per-DAG-node pipeline usage is
# amortized O(1) per node only if results survive across calls.
_memo: Dict["spot.formula", "spot.formula"] = {}


def reset_cache() -> None:
    _memo.clear()


def fold_simplify(f: "spot.formula") -> "spot.formula":
    """Bottom-up unroll-inverse folding over the whole DAG (memoized)."""
    memo = _memo

    def walk(n: "spot.formula") -> "spot.formula":
        hit = memo.get(n)
        if hit is not None:
            return hit
        if n._is(spot.op_And) or n._is(spot.op_Or):
            kids = [walk(c) for c in n]
            out = spot.formula.And(kids) if n._is(spot.op_And) else spot.formula.Or(kids)
            # Constructors flatten/dedupe; fold only what is still boolean.
            if out._is(spot.op_And) or out._is(spot.op_Or):
                out = _fold_node(out)
        elif list(n):
            out = _arm_unpad(n.map(walk))
        else:
            out = n
        memo[n] = out
        return out

    return walk(f)
