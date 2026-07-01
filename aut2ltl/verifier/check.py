"""aut2ltl/verifier/check.py — the non-LTL witness checker (membership tier).

A non-LTL witness is a counting family `(u, v, x, p)`: finite words `u`, `v`, an
ultimately-periodic tail `x = x_prefix . (x_cycle)^w` (a lasso), and a claimed
period `p > 1`, such that membership of `u . v^n . x` toggles with `n mod p`.

This module checks such a family against an INPUT omega-automaton by MEMBERSHIP
only: it asks `u . v^n . x in L` for n = 0..2p via Spot, which decides membership
through automaton intersection and so handles every acceptance type (Buchi, parity,
Rabin, generic Emerson-Lei) uniformly. No internal state is ever referenced — the
check runs on the automaton the client supplied, which is the point: membership is
language-invariant, state indices are not.

SUGGESTIVE TIER. Finitely many membership samples witness phase *distinguishability*
(the tail separates two phases of the v-orbit) but not yet *periodicity*: an
aperiodic language could mimic the pattern up to any finite n. So `ok=True`
corroborates the witness without proving it; `ok=False` (a constant / wrong-period
pattern) is a genuine red flag — the printed certificate does not check out. The
residual-equivalence upgrade that would make this a proof is deferred.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import spot

from aut2ltl.witness import Witness


# --------------------------------------------------------------------------- #
# The single load-bearing primitive: membership of a lasso word in L(A).
# --------------------------------------------------------------------------- #
def member(aut: "spot.twa_graph", word: str) -> bool:
    """True iff the ultimately-periodic omega-word `word` is in L(aut).

    Spot decides this by intersecting `aut` with the one-lasso automaton of the
    word; it is correct for any acceptance condition and any (non)determinism.
    """
    w = spot.parse_word(word, aut.get_dict()).as_automaton()
    return aut.intersects(w)


# --------------------------------------------------------------------------- #
# Building the sampled words  u . v^n . x  in Spot's omega-word syntax.
# Words are lists of letter strings, e.g. ["a", "!a"]; x is (prefix, cycle).
# --------------------------------------------------------------------------- #
def _lasso(prefix: List[str], cycle: List[str]) -> str:
    """Render an ultimately-periodic word as Spot syntax: `l; l; cycle{l; l}`."""
    if not cycle:
        raise ValueError("an omega-word needs a non-empty cycle")
    return "; ".join(prefix + ["cycle{" + "; ".join(cycle) + "}"])


def _sample_word(u: List[str], v: List[str], n: int,
                 x_prefix: List[str], x_cycle: List[str]) -> str:
    """The linear-shape word  u . v^n . x  as a lasso string."""
    return _lasso(u + v * n + x_prefix, x_cycle)


def _sample_word_omega(u: List[str], v: List[str], n: int, y: List[str]) -> str:
    """The ω-power-shape word  u . (v^n . y)^w  as a lasso string."""
    return _lasso(u, v * n + y)


# --------------------------------------------------------------------------- #
# The membership-tier check.
# --------------------------------------------------------------------------- #
def _decide(pattern: List[bool], p: int) -> bool:
    """Whether a sampled membership pattern certifies the claimed period `p`:
    non-constant, periodic with period `p`, and `p`-minimal (a smaller period
    q < p fitting the sample would make the claimed `p` wrong)."""
    non_constant = len(set(pattern)) > 1
    periodic = all(pattern[i] == pattern[i + p] for i in range(len(pattern) - p))
    minimal = all(
        not all(pattern[i] == pattern[i + q] for i in range(len(pattern) - q))
        for q in range(1, p)
    )
    return non_constant and periodic and minimal


def verify_suggestive(
    aut: "spot.twa_graph",
    u: List[str],
    v: List[str],
    x_prefix: List[str],
    x_cycle: List[str],
    p: int,
) -> Tuple[bool, List[bool]]:
    """Sample membership of the linear-shape word `u.v^n.x` for n = 0..2p and
    decide the pattern (`_decide`). Returns `(ok, pattern)`. This is the
    SUGGESTIVE verdict, not yet a periodicity proof."""
    pattern = [
        member(aut, _sample_word(u, v, n, x_prefix, x_cycle))
        for n in range(2 * p + 1)
    ]
    return (_decide(pattern, p), pattern)


def verify_omega(
    aut: "spot.twa_graph",
    u: List[str],
    v: List[str],
    y: List[str],
    p: int,
) -> Tuple[bool, List[bool]]:
    """Sample membership of the ω-power-shape word `u.(v^n.y)^w` for n = 0..2p
    and decide the pattern (`_decide`). Returns `(ok, pattern)`. Same suggestive
    tier as `verify_suggestive` — each sample is one lasso membership."""
    pattern = [
        member(aut, _sample_word_omega(u, v, n, y))
        for n in range(2 * p + 1)
    ]
    return (_decide(pattern, p), pattern)


def samples(w: Witness) -> Optional[List[str]]:
    """The sampled words of a complete `Witness` for n = 0..2p, per its shape —
    linear `u.v^n.x` or ω-power `u.(v^n.y)^w` — as lasso strings; `None` when the
    family is incomplete (nothing to replay)."""
    if not w.complete:
        return None
    if w.omega_power:
        return [_sample_word_omega(w.u or [], w.v, n, w.y or [])
                for n in range(2 * w.p + 1)]
    return [_sample_word(w.u or [], w.v, n, w.x_prefix or [], w.x_cycle or [])
            for n in range(2 * w.p + 1)]


def verify_with(
    member_of: "Callable[[str], bool]", w: Witness
) -> Tuple[Optional[bool], List[bool]]:
    """Check a `Witness` through an arbitrary membership predicate (one lasso
    string in, its membership out). Lets a caller replay against a language it
    can only query compositionally (e.g. the connective of a split's parts).
    Returns `(ok, pattern)`; `(None, [])` on an incomplete family."""
    words = samples(w)
    if words is None:
        return (None, [])
    pattern = [member_of(word) for word in words]
    return (_decide(pattern, w.p), pattern)


def verify(aut: "spot.twa_graph", w: Witness) -> Tuple[Optional[bool], List[bool]]:
    """Check a `Witness` against `aut` by membership, dispatching on its shape.
    Returns `(ok, pattern)`; `(None, [])` when the family is incomplete, which the
    caller reads as "no checkable witness", not a failure."""
    return verify_with(lambda word: member(aut, word), w)


__all__ = ["member", "verify_suggestive", "verify_omega", "verify"]
