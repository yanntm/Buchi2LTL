"""
factor_pass.py — Rule 3: partial factoring at Or nodes.

Greedy shared-term factoring, the SOUND form of the draft script's idea:
only the disjuncts that contain the chosen term are grouped; the rest stay
outside (the draft wrapped everything — `(a&Xb)|(a&Xc)|Xd` came out as
`a&(Xb|Xc|Xd)`, strictly smaller language, witness cycle{!a&d}):

    (t ∧ A) ∨ (t ∧ B) ∨ C   →   (t ∧ (A ∨ B)) ∨ C       [distributivity]

Repeatedly: count conjunct frequency across And-disjuncts (a bare disjunct
counts as the singleton conjunction of itself), factor the most frequent
term with count ≥ 2, iterate — each round strictly reduces the disjunct
count, so it terminates. The grouped inner Or is factored recursively.

Purely-propositional Or nodes (and inner guard groups) are additionally
minimized through the BDD → Minato-ISOP round-trip (`prop_minimize`),
accepted only when not larger — ISOP is irredundant, not always minimal.

Whole pass is a memoized bottom-up walk: O(DAG).
"""

from __future__ import annotations
from collections import Counter
from typing import Dict

import spot

from .now_eval import prop_minimize


def _tree_size(f: "spot.formula") -> int:
    seen = set()
    stack = [f]
    n = 0
    while stack:
        g = stack.pop()
        if g in seen:
            continue
        seen.add(g)
        n += 1
        stack.extend(g)
    return n


def _minimize_if_smaller(f: "spot.formula") -> "spot.formula":
    m = prop_minimize(f)
    if m is not None and _tree_size(m) <= _tree_size(f):
        return m
    return f


def _conjuncts(f: "spot.formula"):
    return list(f) if f._is(spot.op_And) else [f]


def _factor_or(node: "spot.formula") -> "spot.formula":
    """Factor one Or node (children assumed already processed)."""
    if node.is_boolean():
        return _minimize_if_smaller(node)
    work = list(node)
    while True:
        freq: Counter = Counter()
        for k in work:
            for c in _conjuncts(k):
                freq[c] += 1
        if not freq:
            break
        best, cnt = freq.most_common(1)[0]
        if cnt < 2:
            break
        ins, outs = [], []
        for k in work:
            cs = _conjuncts(k)
            if best in cs:
                rest = [c for c in cs if c != best]
                ins.append(spot.formula.And(rest) if rest else spot.formula.tt())
            else:
                outs.append(k)
        sub = spot.formula.Or(ins)
        if sub._is(spot.op_Or):
            sub = _factor_or(sub)
        elif sub.is_boolean():
            sub = _minimize_if_smaller(sub)
        composite = spot.formula.And([best, sub])
        if not outs:
            return composite
        work = outs + [composite]
    return spot.formula.Or(work)


# Persistent memo (see context_pass note): per-DAG-node pipeline usage is
# amortized O(1) per node only if results survive across calls.
_memo: Dict["spot.formula", "spot.formula"] = {}


def reset_cache() -> None:
    _memo.clear()


def factor_simplify(f: "spot.formula") -> "spot.formula":
    """Bottom-up partial factoring over the whole DAG (memoized)."""
    memo = _memo

    def walk(n: "spot.formula") -> "spot.formula":
        hit = memo.get(n)
        if hit is not None:
            return hit
        if n._is(spot.op_And):
            out = spot.formula.And([walk(c) for c in n])
        elif n._is(spot.op_Or):
            out = _factor_or(spot.formula.Or([walk(c) for c in n]))
        elif list(n):
            out = n.map(walk)
        else:
            out = n
        memo[n] = out
        return out

    return walk(f)
