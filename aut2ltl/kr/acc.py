"""
acc.py — config-indexed Acc(c) dispatch for the bounded / transient fragment.

Reconstructs the LTL for cascades whose runs reach a ⊤/⊥ sink within a bounded
horizon (the "X-ladder" fragment, e.g. X(a & Xa)). The language from the initial
config is then a finite unrolling — the literal small formula — so this dispatch
emits that unrolling directly and bypasses the cascade reach machinery entirely
(no fin_c, reach_strong, or operator-counter reset), avoiding the reach τ-tail
blow-up the general Muller form pays on these inputs.

Self-gating: a config re-entered on the unroll path that is not a ⊤/⊥ sink is
recurrent — the input is outside the bounded fragment — so `Acc` declines and the
caller falls back to the Büchi/coBüchi/Muller chain. The ⊤/⊥ test is a Spot
oracle on the small INPUT automaton D (per state, lazy + cached), never on the
output formula; the build is O(|reachable configs| × |Σ|) memoized.

`Acc` is a self-contained CascadeTranslator member: it decides on its own whether
the input is in the bounded fragment (no external predicate) and returns a
language-faithful LTLFormulaResult or a DECLINE.
"""

from __future__ import annotations
from typing import Optional

import aut2ltl.kr.reachability_operators as _ops
from aut2ltl.kr.ltl_builders import _And, _Or, _X, _tt, _ff, _simp_f, _tree_size_f, _letters_to_f
from aut2ltl.kr.cascade import Cascade
from aut2ltl.contract import LTLFormulaResult, CascadeTranslator


class _Recurrent(Exception):
    """Raised when the unroll re-enters a non-⊤/⊥ config (recurrent ⇒ not the
    bounded fragment); aborts Acc so the caller falls back to BLS."""


def _unroll(casc: Cascade) -> Optional["spot.formula"]:
    """The bounded Acc(ι) unroll: the formula for L(D) from the initial config,
    or None if any reachable config is recurrent (input outside the bounded
    fragment). `Acc` wraps this into a LTLFormulaResult.

      Acc(c) = ⊤  if L(D from state_of(c)) is universal,           (R1 base)
             = ⊥  if it is empty,
             = ⋁_σ guard(σ) ∧ X Acc(move_config(c,σ))  otherwise.  (R2 unroll)

    The ⊤/⊥ oracle is LAZY (per state, on demand, cached) so a case that declines
    pays only for the few states on the path before the first cycle, not all n."""
    D = casc.original_aut
    if D is None or casc.num_levels == 0:
        return None
    import spot

    # Lazy ⊤/⊥ oracle on D from a state q (cached). D is the small input
    # automaton — universality on a deterministic n-state aut is cheap, and this
    # never touches the (large) output formula.
    _Dq = None
    _true = None
    base_memo: dict = {}     # state q -> _tt()/_ff()/None (None = neither ⊤ nor ⊥)

    def _base(q):
        nonlocal _Dq, _true
        if q in base_memo:
            return base_memo[q]
        if _Dq is None:
            _Dq = spot.automaton(D.to_str("hoa"))   # one mutable copy, re-pointed
            _true = spot.formula("1").translate()
        _Dq.set_init_state(q)
        if _Dq.is_empty():
            base_memo[q] = _ff()
        elif spot.are_equivalent(_Dq, _true):
            base_memo[q] = _tt()
        else:
            base_memo[q] = None
        return base_memo[q]

    iota = None
    try:
        iota = casc.state_to_config.get(D.get_init_state_number())
    except Exception:
        pass
    if iota is None:
        r = casc.reachable_configs()
        iota = r[0] if r else None
    if iota is None:
        return None

    nl = casc.num_letters()
    memo: dict = {}
    stack: set = set()

    def step(c):
        if c in memo:
            return memo[c]
        q = casc.state_of(c)
        if q is not None:
            b = _base(q)
            if b is not None:               # R1: ⊤ / ⊥ sink
                memo[c] = b
                return b
        if c in stack:                      # recurrent non-trivial config
            raise _Recurrent()
        stack.add(c)
        terms = []
        for li in range(nl):
            g = _letters_to_f(casc.letter_valuations[li], casc.aps)
            terms.append(_And(g, _X(step(casc.move_config(c, li)))))
        stack.discard(c)
        memo[c] = _simp_f(_Or(*terms))
        return memo[c]

    try:
        res = step(iota)
    except _Recurrent:
        return None
    _ops.PAPER_MAX_LTL_SIZE = _tree_size_f(res)
    return res


class Acc:
    """Config-indexed Acc(c) member — the bounded / transient (X-ladder)
    fragment. Self-gating: declines when the cascade is outside that fragment."""

    name = "acc"

    def __call__(self, casc: Cascade) -> LTLFormulaResult:
        phi = _unroll(casc)
        if phi is None:
            return LTLFormulaResult.decline()
        return LTLFormulaResult(formula=phi, technique={self.name})


acc: CascadeTranslator = Acc()


__all__ = ["Acc", "acc"]
