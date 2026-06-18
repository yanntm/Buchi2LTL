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

from .now_eval import _prop_bdd, _ctx_bdd, _entails, _entails_not, prop_cofactor
from .factor_pass import _tree_size


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
    # ----------------------------------------------------------------------
    # INDEPENDENT RULE (logically unrelated to the X-unrolling folds above;
    # shares only this finder's (i, j, rep) return protocol). The weak-until
    # law  f W g ≡ G f ∨ (f U g), with the construction's ¬g-strengthened G
    # body, which is sound because  G(f ∧ ¬g) ∨ (f U g) ≡ G f ∨ (f U g):
    #     G f         ∨ (f U g)   → f W g
    #     G(f ∧ ¬g)   ∨ (f U g)   → f W g
    # Trades two temporals (G, U) for one (W) — an acc-set census win like the
    # rules above. Match on the U disjunct's arms; the G body must be exactly
    # f, or f with a single ¬g conjunct added (any other extra conjunct makes
    # G(body) strictly stronger than G f, so the fold would be UNSOUND).
    for j, u in enumerate(kids):
        if not u._is(spot.op_U):
            continue
        f, g = u[0], u[1]
        for i, k in enumerate(kids):
            if i == j or not k._is(spot.op_G):
                continue
            body = k[0]
            if body == f:
                return i, j, spot.formula.W(f, g)
            if body._is(spot.op_And):
                conj = list(body)
                for s in conj:
                    if _is_neg(s, g) and \
                            spot.formula.And([t for t in conj if t != s]) == f:
                        return i, j, spot.formula.W(f, g)
    # ----------------------------------------------------------------------
    # INDEPENDENT RULE — the M-disjunct sibling of the W-fold above (the same
    # Or-node "G ∨ modal" shape, M in place of U). The release law
    #   f R g ≡ G g ∨ (f M g),  with the construction's ¬f-strengthened G body,
    # sound because  G(g ∧ ¬f) ∨ (f M g) ≡ G g ∨ (f M g):
    #     G g         ∨ (f M g)   → f R g
    #     G(g ∧ ¬f)   ∨ (f M g)   → f R g
    # Trades two temporals (G, M) for one (R). Match on the M disjunct's arms;
    # the G body must be exactly g, or g with a single ¬f conjunct added (any
    # other extra conjunct makes G(body) strictly stronger than G g — UNSOUND).
    for j, m in enumerate(kids):
        if not m._is(spot.op_M):
            continue
        f, g = m[0], m[1]
        for i, k in enumerate(kids):
            if i == j or not k._is(spot.op_G):
                continue
            body = k[0]
            if body == g:
                return i, j, spot.formula.R(f, g)
            if body._is(spot.op_And):
                conj = list(body)
                for s in conj:
                    if _is_neg(s, f) and \
                            spot.formula.And([t for t in conj if t != s]) == g:
                        return i, j, spot.formula.R(f, g)
    # ----------------------------------------------------------------------
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
    # ----------------------------------------------------------------------
    # INDEPENDENT RULE — the dual of the W-fold in _find_fold_or: the strong
    # release law  f M g ≡ F f ∧ (f R g), with the ¬g-weakened F body, sound
    # because  F(f ∨ ¬g) ∧ (f R g) ≡ F f ∧ (f R g):
    #     F f         ∧ (f R g)   → f M g
    #     F(f ∨ ¬g)   ∧ (f R g)   → f M g
    # Match on the R conjunct's arms; the F body must be exactly f, or f with
    # a single ¬g disjunct added (any other extra disjunct makes F(body)
    # strictly weaker than F f, so the fold would be UNSOUND).
    for j, r in enumerate(kids):
        if not r._is(spot.op_R):
            continue
        f, g = r[0], r[1]
        for i, k in enumerate(kids):
            if i == j or not k._is(spot.op_F):
                continue
            body = k[0]
            if body == f:
                return i, j, spot.formula.M(f, g)
            if body._is(spot.op_Or):
                disj = list(body)
                for s in disj:
                    if _is_neg(s, g) and \
                            spot.formula.Or([t for t in disj if t != s]) == f:
                        return i, j, spot.formula.M(f, g)
    # ----------------------------------------------------------------------
    # INDEPENDENT RULE — the W-conjunct sibling of the M-fold above (the dual
    # of the R-fold in _find_fold_or). The until law
    #   f U g ≡ F g ∧ (f W g),  with the construction's ¬f-weakened F body,
    # sound because  F(g ∨ ¬f) ∧ (f W g) ≡ F g ∧ (f W g):
    #     F g         ∧ (f W g)   → f U g
    #     F(g ∨ ¬f)   ∧ (f W g)   → f U g
    # Trades two temporals (F, W) for one (U). Match on the W conjunct's arms;
    # the F body must be exactly g, or g with a single ¬f disjunct added (any
    # other extra disjunct makes F(body) strictly weaker than F g — UNSOUND).
    for j, w in enumerate(kids):
        if not w._is(spot.op_W):
            continue
        f, g = w[0], w[1]
        for i, k in enumerate(kids):
            if i == j or not k._is(spot.op_F):
                continue
            body = k[0]
            if body == g:
                return i, j, spot.formula.U(f, g)
            if body._is(spot.op_Or):
                disj = list(body)
                for s in disj:
                    if _is_neg(s, f) and \
                            spot.formula.Or([t for t in disj if t != s]) == g:
                        return i, j, spot.formula.U(f, g)
    # ----------------------------------------------------------------------
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


def _arm_cofactor(node: "spot.formula") -> "spot.formula":
    """Boolean left-arm cofactoring of a binary temporal (both arms pure
    propositional):

        φ U ψ ≡ φ' U ψ    when φ' agrees with φ on {ψ false}   (same for W)
        φ R ψ ≡ φ' R ψ    when φ' agrees with φ on {ψ true}    (same for M)

    e.g. `(a ∧ ¬b) U b → a U b`. Soundness (U): the earliest position
    where ψ fires is the canonical witness; at every position strictly
    before it ψ is false, and the left arm is evaluated only there — so any
    φ' that matches φ wherever ψ is false yields the same word set. R/M are
    the literal duals (left arm matters only where ψ holds), via `φ R ψ ≡
    ¬(¬φ U ¬ψ)`. The Couvreur acc-set census is untouched (no temporal node
    added/removed); the left arm is the restrict of φ to that care-set,
    re-expressed by Minato-ISOP and accepted only when strictly smaller."""
    if node._is(spot.op_U) or node._is(spot.op_W):
        f, g = node[0], node[1]
        f2 = prop_cofactor(f, g, care_true=False)        # care-set {ψ false}
        if f2 is not None and _tree_size(f2) < _tree_size(f):
            op = spot.formula.U if node._is(spot.op_U) else spot.formula.W
            return op(f2, g)
    elif node._is(spot.op_R) or node._is(spot.op_M):
        f, g = node[0], node[1]
        f2 = prop_cofactor(f, g, care_true=True)          # care-set {ψ true}
        if f2 is not None and _tree_size(f2) < _tree_size(f):
            op = spot.formula.R if node._is(spot.op_R) else spot.formula.M
            return op(f2, g)
    return node


def _gffg_cofactor(node: "spot.formula") -> "spot.formula":
    """INDEPENDENT RULE — GF/FG sibling cofactoring (boolean args only),
    unrelated to the folds above; applied directly to a boolean node:

        GF φ ∧ FG ψ   →   GF(φ|ψ)  ∧ FG ψ     φ restricted to {ψ true}
        FG α ∨ GF β   →   FG(α|¬β) ∨ GF β      α restricted to {β false}

    GF is a tail (infinitely-often) property, so under the cofinite invariant
    FG ψ the GF argument only ever matters where ψ holds — restrict it there
    (Coudert–Madre, `prop_cofactor`). The Or form is the literal dual: the FG
    disjunct matters only when GF β fails, i.e. cofinitely ¬β. The care-set
    aggregates every sibling invariant — `∧ ψ_k` (And) / `∧ ¬β_k = ¬(∨ β_k)`
    (Or) — so it is built as And(ψ_k)|care_true (resp. Or(β_k)|¬care). Inner
    arguments must be propositional; accept only when strictly smaller. No
    temporal node added or removed (Couvreur acc-set census untouched)."""
    is_and = node._is(spot.op_And)
    if not (is_and or node._is(spot.op_Or)):
        return node
    # AND: shrink GF=G(F·) via the FG=F(G·) invariants; OR: dual.
    shrink_o, shrink_i = (spot.op_G, spot.op_F) if is_and else (spot.op_F, spot.op_G)
    inv_o, inv_i = (spot.op_F, spot.op_G) if is_and else (spot.op_G, spot.op_F)
    rebuild = ((lambda p: spot.formula.G(spot.formula.F(p))) if is_and
               else (lambda p: spot.formula.F(spot.formula.G(p))))

    def _nest_body(k: "spot.formula", outer, inner) -> "Optional[spot.formula]":
        if k._is(outer) and k[0]._is(inner) and k[0][0].is_boolean():
            return k[0][0]
        return None

    # Invariant SOURCE: the literal FG(x)/GF(x), OR a strong until/release that
    # ENTAILS it. `φ U G(x) ⟹ FG x` for any φ (And side); dually the Or disjunct
    # `φ R F(x)`, false only when `¬φ U G(¬x) ⟹ FG ¬x`, supplies the same ¬x
    # co-invariant `GF x` does. W/M give NO invariant — their Gφ/G¬φ branch breaks
    # the entailment (the strong-until dual of why W is excluded on the And side).
    bin_inv = spot.op_U if is_and else spot.op_R
    def _inv_body(k: "spot.formula") -> "Optional[spot.formula]":
        b = _nest_body(k, inv_o, inv_i)
        if b is not None:
            return b
        if k._is(bin_inv) and k[1]._is(inv_i) and k[1][0].is_boolean():
            return k[1][0]                          # U(_, G x) / R(_, F x) → x
        return None

    kids = list(node)
    invs = [b for b in (_inv_body(k) for k in kids) if b is not None]
    if not invs:
        return node
    # And -> care-set ∧ψ_k (care_true); Or -> care-set ¬(∨β_k) (¬care_true).
    care = spot.formula.And(invs) if is_and else spot.formula.Or(invs)
    changed = False
    out: List["spot.formula"] = []
    for k in kids:
        phi = _nest_body(k, shrink_o, shrink_i)
        if phi is not None:
            phi2 = prop_cofactor(phi, care, care_true=is_and)
            if phi2 is not None and _tree_size(phi2) < _tree_size(phi):
                out.append(rebuild(phi2))
                changed = True
                continue
        out.append(k)
    if not changed:
        return node
    return spot.formula.And(out) if is_and else spot.formula.Or(out)


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
                out = _gffg_cofactor(_fold_node(out))
        elif list(n):
            out = _arm_cofactor(_arm_unpad(n.map(walk)))
        else:
            out = n
        memo[n] = out
        return out

    return walk(f)
