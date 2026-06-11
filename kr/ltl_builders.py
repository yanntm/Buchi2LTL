"""
ltl_builders.py — LTL guard helpers, simplification, and native spot.formula builders.

Shared leaf utilities for the KR construction: valuation→guard strings,
Spot-based simplification/normalization, and small wrappers over spot.formula
for native DAG construction (sharing, auto simplify, hashable cache keys).
No dependencies on other kr/ modules.
"""

from __future__ import annotations
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


def _simp_f(f: "spot.formula") -> "spot.formula":
    """Simplify a spot.formula, returning a spot.formula (no string round-trip)."""
    global _tl_simp
    if f is None:
        return _ff()
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


def _short_f(f: spot.formula, n: int = 120) -> str:
    """Truncated stringification for trace lines (full str() of a huge shared
    DAG is O(unfolded size); only call under an enabled-trace guard)."""
    s = _str_f(f)
    return s if len(s) <= n else s[:n] + "..."
