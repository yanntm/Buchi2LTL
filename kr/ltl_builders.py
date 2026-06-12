"""
ltl_builders.py — LTL guard helpers, simplification, and native spot.formula builders.

Shared leaf utilities for the KR construction: valuation→guard strings,
Spot-based simplification/normalization, and small wrappers over spot.formula
for native DAG construction (sharing, auto simplify, hashable cache keys).
No dependencies on other kr/ modules.
"""

from __future__ import annotations
import os
from typing import Callable, Dict, List, Optional

import spot


# ---------------------------------------------------------------------------
# Guard helpers (valuation -> LTL prop formula string)
# ---------------------------------------------------------------------------

def letters_to_prop(valuation: Dict[str, bool], aps: List[str]) -> str:
    """Turn a valuation into a conjunction string like 'p & !q & r' for use in LTL."""
    parts = []
    for ap in aps:
        if valuation.get(ap, False):
            parts.append(ap)
        else:
            parts.append(f"!{ap}")
    return " & ".join(parts) if parts else "true"


def make_guard(valuations: List[Dict[str, bool]], aps: List[str], pred: Callable[[Dict[str, bool]], bool] = lambda v: True) -> str:
    """Build a disjunctive guard: OR of letters satisfying pred (default: all)."""
    good = [letters_to_prop(v, aps) for v in valuations if pred(v)]
    if not good:
        return "false"
    if len(good) == 1:
        return good[0]
    return "(" + " | ".join(good) + ")"


# ---------------------------------------------------------------------------
# Simplification / normalization
# ---------------------------------------------------------------------------

# One shared simplifier for the whole construction: its internal cache persists
# across calls, so repeatedly simplifying shared subformulas (hash-consed
# spot.formula nodes) is amortized O(1) instead of a fresh tree walk each time.
_tl_simp: Optional["spot.tl_simplifier"] = None


# Spot tl_simplifier policy for the construction path. Pure-LTL rewriting is
# weak on our recursive cascade shapes, and the simplifier is not fully
# sharing-aware: a single simplify of a big Or/And can stall for minutes
# inside C++ where even SIGALRM cannot fire (watchdogged on "(a U b) | Gc").
# The construction therefore relies on spot.formula's constructor-level
# trivial identities (hash-consing, constant folding, dedup) and calls
# tl_simplifier only when asked:
#   KR_SIMP_TREE_LIMIT = 0   (default) never simplify — hash-cons only
#   KR_SIMP_TREE_LIMIT = N>0 simplify only formulas with <= N unfolded nodes
#   KR_SIMP_TREE_LIMIT < 0   always simplify (legacy behavior)
# Skipping is always safe: simplification is cosmetic, never semantic.
# The size guard uses the unfolded (tree) size — the honest cost proxy for a
# sharing-blind walk — which unlike DAG size is compositional
# (1 + sum of child sizes) and so memoizes by node id: O(arity) per NEW node.
_SIMP_TREE_LIMIT = int(os.getenv("KR_SIMP_TREE_LIMIT", "0"))
_SIMP_TREE_SAT = 1 << 60  # saturation: sizes beyond any cap are all equal
_tree_size_memo: Dict[int, int] = {}


def _tree_size_f(f: "spot.formula") -> int:
    """Memoized unfolded-tree node count (saturating)."""
    gid = f.id()
    hit = _tree_size_memo.get(gid)
    if hit is not None:
        return hit
    total = 1
    for child in f:
        total += _tree_size_f(child)
        if total >= _SIMP_TREE_SAT:
            total = _SIMP_TREE_SAT
            break
    _tree_size_memo[gid] = total
    return total


def _simp_f(f: "spot.formula") -> "spot.formula":
    """Normalize a spot.formula for the construction path (no string
    round-trip). By default this is the identity (hash-cons only); see the
    _SIMP_TREE_LIMIT policy note above for the opt-in tl_simplifier modes."""
    global _tl_simp
    if f is None:
        return _ff()
    if _SIMP_TREE_LIMIT == 0:
        return f
    if _SIMP_TREE_LIMIT > 0 and _tree_size_f(f) > _SIMP_TREE_LIMIT:
        return f
    if _tl_simp is None:
        _tl_simp = spot.tl_simplifier()
    try:
        return _tl_simp.simplify(f)
    except Exception:
        return f


def simplify_ltl(expr: "str | spot.formula") -> str:
    """Simplify an LTL formula (string or spot.formula) using Spot; returns str.
    Purely algebraic on the produced expr; no aut shape used.
    """
    if isinstance(expr, spot.formula):
        return _normalize_ltl(str(_simp_f(expr)))
    if not expr or expr in ("true", "false"):
        return expr
    try:
        return _normalize_ltl(str(_simp_f(spot.formula(expr))))
    except Exception:
        return _normalize_ltl(expr)  # keep as-is if cannot simplify


def _normalize_ltl(s: str) -> str:
    """Spot often uses 1/0 for true/false (parses words but outputs 0/1 in many cases).
    Normalize for consistent I/O and tests.
    """
    if s in ("1", "true"):
        return "true"
    if s in ("0", "false"):
        return "false"
    return s


def normalize_ltl(expr: str) -> str:
    """Normalize + simplify (Spot 0/1 -> true/false words for nicer output and test I/O)."""
    return simplify_ltl(expr)


# ---------------------------------------------------------------------------
# Spot formula builders
# Native spot.formula for construction (DAG sharing, auto simplify, better keys)
# instead of string building + repeated parse/simp for subformulas.
# Public API of the operators still returns str for compat; internals use these.
# ---------------------------------------------------------------------------

def _tt() -> spot.formula:
    return spot.formula.tt()

def _ff() -> spot.formula:
    return spot.formula.ff()

def _ap(name: str) -> spot.formula:
    return spot.formula.ap(name)

def _And(*fs: Optional[spot.formula]) -> spot.formula:
    fs = [f for f in fs if f is not None]
    if not fs:
        return _tt()
    if len(fs) == 1:
        return fs[0]
    return spot.formula.And(list(fs))

def _Or(*fs: Optional[spot.formula]) -> spot.formula:
    fs = [f for f in fs if f is not None]
    if not fs:
        return _ff()
    if len(fs) == 1:
        return fs[0]
    return spot.formula.Or(list(fs))

def _Not(f: Optional[spot.formula]) -> spot.formula:
    if f is None:
        return _ff()
    return spot.formula.Not(f)

def _X(f: spot.formula) -> spot.formula:
    return spot.formula.X(f)

def _U(f: spot.formula, g: spot.formula) -> spot.formula:
    return spot.formula.U(f, g)

def _F(f: spot.formula) -> spot.formula:
    return _U(_tt(), f)

def _G(f: spot.formula) -> spot.formula:
    return _Not(_F(_Not(f)))

def _to_f(x: Optional[str | spot.formula]) -> spot.formula:
    """Convert str or formula to spot.formula. Used for beta/tau inputs."""
    if x is None:
        return _ff()
    if isinstance(x, spot.formula):
        return x
    s = str(x).strip().lower()
    if s in ("true", "1", "t"):
        return _tt()
    if s in ("false", "0", "f"):
        return _ff()
    try:
        return spot.formula(str(x))
    except Exception:
        return _tt()  # safe fallback

def _letters_to_f(valuation: Dict[str, bool], aps: List[str]) -> spot.formula:
    """Valuation to conjunction as spot.formula (replaces letters_to_prop str)."""
    parts = []
    for ap_name in aps:
        v = valuation.get(ap_name, False)
        fap = _ap(ap_name)
        parts.append(fap if v else _Not(fap))
    if not parts:
        return _tt()
    res = parts[0]
    for p in parts[1:]:
        res = _And(res, p)
    return res

def _str_f(f: spot.formula) -> str:
    """Convert formula to normalized str — top-level output and traces ONLY.
    Pure stringification: no simplify (that was a per-conversion tree walk that
    dominated construction time; use _simp_f explicitly where wanted)."""
    if f is None:
        return "false"
    return _normalize_ltl(str(f))


_FLATTEN_TREE_LIMIT = int(os.getenv("KR_FLATTEN_TREE_LIMIT", "250000"))


def _str_f_gated(f: spot.formula, limit: Optional[int] = None) -> str:
    """Flatten only when the unfolded tree is small enough; otherwise return a
    placeholder naming the size (never pay O(tree) blind). Gate shared with
    trace_fin: KR_FLATTEN_TREE_LIMIT, default 250k tree nodes ≈ 2MB string."""
    if f is None:
        return "false"
    lim = _FLATTEN_TREE_LIMIT if limit is None else limit
    n = _tree_size_f(f)
    if 0 <= lim < n:
        return f"<unflattened DAG: {n} tree nodes>"
    return _str_f(f)


def _short_f(f: spot.formula, n: int = 120) -> str:
    """Truncated stringification for trace lines (full str() of a huge shared
    DAG is O(unfolded size); only call under an enabled-trace guard)."""
    s = _str_f(f)
    return s if len(s) <= n else s[:n] + "..."
