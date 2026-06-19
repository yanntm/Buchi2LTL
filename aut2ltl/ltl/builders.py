"""
ltl/builders.py — LTL guard helpers, simplification, and native spot.formula builders.

Generic, engine-agnostic leaf utilities (the `aut2ltl.ltl` floor package):
valuation→guard strings, Spot-based simplification/normalization (the own-rules
pass in `aut2ltl.ltl.simplify`), and small wrappers over spot.formula for native
DAG construction (sharing, auto simplify, hashable cache keys). Imports no engine
(`kr`/`sl`) — only `aut2ltl.ltl.simplify`, `spot`, and `buddy`.
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

# Shared simplifier instances for the whole construction (see _get_tl_simp):
# their internal caches persist across calls, so repeatedly simplifying shared
# subformulas (hash-consed spot.formula nodes) is amortized O(1) instead of a
# fresh tree walk each time.


# Spot tl_simplifier policy for the construction path.
#
# Default mode (KR_SIMP_NODE=1): simplify ONCE PER DAG NODE, memoized by
# node id. The old failure mode was simplify-on-the-unfolded-tree (a single
# call on a big Or/And stalled minutes inside C++, watchdogged on
# "(a U b) | Gc"); per-node + id-memo changes the cost model: every _simp_f
# call sees children that were already simplified (operators build bottom-up
# through these builders), our memo prevents re-entering C++ for any node
# seen before, and the ONE shared tl_simplifier instance keeps its internal
# cache across calls. This is what kills vacuous structure at construction
# time (X(0)→0, σ∧0→0, absorption …) — dead tails then collapse memo keys in
# the operators and delete whole wrapped-descendant subtrees (see
# bls/dag_folding.md counter-measure A). KR_SIMP_NODE=0 is the escape hatch
# if Spot ever becomes the blocker (then we grow our own small rule set).
#
# Legacy tree-size policy (only when KR_SIMP_NODE=0):
#   KR_SIMP_TREE_LIMIT = 0   never simplify — hash-cons only
#   KR_SIMP_TREE_LIMIT = N>0 simplify only formulas with <= N unfolded nodes
#   KR_SIMP_TREE_LIMIT < 0   always simplify (historical behavior)
# Skipping is always safe: simplification is cosmetic, never semantic.
_SIMP_NODE = os.getenv("KR_SIMP_NODE", "1").lower() not in ("0", "false", "no", "off")
_SIMP_TREE_LIMIT = int(os.getenv("KR_SIMP_TREE_LIMIT", "0"))
_simp_memo: Dict[int, "spot.formula"] = {}

# KR_SIMP_OPTS policy (measured 2026-06-12 on the (a&Xa) anatomy):
#   basics — constant folding / unit rules only (X(0)→0 and friends);
#            never stalls. a&Xa: 752→599 subproblems.
#   full   — adds Spot's syntactic-implication machinery, which recurses
#            operand PAIRS sharing-blind (quadratic × deep): best folding
#            (a&Xa: 752→311) but X(a&Xa) 5L blew a 15s budget per-node.
#   hybrid (default) — full rules for nodes whose memoized unfolded-tree
#            size is ≤ KR_SIMP_FULL_LIMIT, basics above: full's folding
#            where it's affordable, never the quadratic blowup on giants.
_SIMP_OPTS = os.getenv("KR_SIMP_OPTS", "hybrid").lower()
_SIMP_FULL_LIMIT = int(os.getenv("KR_SIMP_FULL_LIMIT", "2000"))
_tl_simp_basic: Optional["spot.tl_simplifier"] = None
_tl_simp_full: Optional["spot.tl_simplifier"] = None


def _get_tl_simp(full: bool) -> "spot.tl_simplifier":
    global _tl_simp_basic, _tl_simp_full
    if full:
        if _tl_simp_full is None:
            _tl_simp_full = spot.tl_simplifier()
        return _tl_simp_full
    if _tl_simp_basic is None:
        opts = spot.tl_simplifier_options(
            True,   # basics
            False,  # synt_impl
            False,  # event_univ
        )
        _tl_simp_basic = spot.tl_simplifier(opts)
    return _tl_simp_basic


def _want_full(f: "spot.formula") -> bool:
    if _SIMP_OPTS == "full":
        return True
    if _SIMP_OPTS == "basics":
        return False
    return _tree_size_f(f) <= _SIMP_FULL_LIMIT
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


# Own rewrite pass (bls/simplify: context propagation, now-evaluation,
# partial factoring — rules Spot does not have; see bls/simplify/README.md).
# Runs per node AFTER Spot's pass; persistent memos in bls/simplify make
# this amortized O(1) per distinct node. KR_SIMP_OWN=0 disables.
# Size cap (same rationale as the hybrid full/basics policy): factoring and
# sibling contexts on GIANT top-level nodes cost more than they fold —
# uncapped, the 3-4L reactivity cases went from seconds to CONSTRUCT_TIMEOUT.
# Bottom-up construction means small/mid nodes carry the reduction anyway.
_SIMP_OWN = os.getenv("KR_SIMP_OWN", "1").lower() not in ("0", "false", "no", "off")
_SIMP_OWN_LIMIT = int(os.getenv("KR_SIMP_OWN_LIMIT", "2000"))


_own_dict_shared = False


def _own_simp(f: "spot.formula") -> "spot.formula":
    if not _SIMP_OWN:
        return f
    if 0 <= _SIMP_OWN_LIMIT < _tree_size_f(f):
        return f
    try:
        global _guard_bdd_dict, _guard_bdd_owner, _own_dict_shared
        from aut2ltl.ltl import simplify as _krs
        if not _own_dict_shared:
            # one bdd_dict per process: a second dict next to the fusion
            # one corrupted the heap in equiv children (F(a&Xb) crash)
            if _guard_bdd_dict is None:
                _guard_bdd_dict = spot.make_bdd_dict()
                _guard_bdd_owner = spot.make_twa_graph(_guard_bdd_dict)
            _krs.now_eval.use_bdd_dict(_guard_bdd_dict, _guard_bdd_owner)
            _own_dict_shared = True
        return _krs.simplify_node(f)
    except Exception:
        return f


def own_simplify(f: "spot.formula") -> "spot.formula":
    """Public entry to the bls/simplify own-rules pass (NO Spot tl_simplifier —
    Spot's simplifier is not DAG-size aware, so it is deliberately excluded
    here). Used by the portfolio combinators to fold a recombined formula
    that no per-node pass ever saw as a whole (e.g. `G(!b&h) | (h U b)` →
    `h W b` after an Or-recombine). Shares the process bdd_dict and the
    KR_SIMP_OWN size guard via `_own_simp`; identity on failure."""
    return _own_simp(f)


def _simp_f(f: "spot.formula") -> "spot.formula":
    """Normalize a spot.formula for the construction path (no string
    round-trip). Default: per-DAG-node memoized tl_simplifier (see policy
    note above) followed by the bls/simplify own-rules pass. With
    KR_SIMP_NODE=0 falls back to the legacy tree-size policy
    (_SIMP_TREE_LIMIT)."""
    if f is None:
        return _ff()
    if _SIMP_NODE:
        gid = f.id()
        hit = _simp_memo.get(gid)
        if hit is not None:
            return hit
        try:
            res = _get_tl_simp(_want_full(f)).simplify(f)
        except Exception:
            res = f
        res2 = _own_simp(res)
        if res2 is not res and res2 != res:
            # our rules fired: let Spot close what they exposed (X(0),
            # F-merge, …) — one bounded extra pass, then fixpoint.
            try:
                res2 = _get_tl_simp(_want_full(res2)).simplify(res2)
            except Exception:
                pass
        res = res2
        _simp_memo[gid] = res
        _simp_memo[res.id()] = res  # simplify is idempotent — fixpoint entry
        return res
    if _SIMP_TREE_LIMIT == 0:
        return f
    if _SIMP_TREE_LIMIT > 0 and _tree_size_f(f) > _SIMP_TREE_LIMIT:
        return f
    try:
        return _get_tl_simp(_want_full(f)).simplify(f)
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

# ---------------------------------------------------------------------------
# Guard fusion (letter fusion, dag_folding.md counter-measure B)
# ---------------------------------------------------------------------------

# Process-lifetime bdd_dict + owner: spot's bdd_dict aborts the process at
# destruction if variables stay registered, so the dict and its owning
# twa_graph (the bindings' only accepted owner type) live as long as we do.
_guard_bdd_dict = None
_guard_bdd_owner = None


def _fuse_or(fs: List["spot.formula"]) -> "spot.formula":
    """OR of PROPOSITIONAL guards, minimized via BDD + Minato ISOP
    (spot.bdd_to_formula). Falls back to the plain Or on any failure —
    fusion correctness never depends on the minimization, only output size.
    """
    if not fs:
        return _ff()
    if len(fs) == 1:
        return fs[0]
    or_f = _Or(*fs)
    global _guard_bdd_dict, _guard_bdd_owner
    try:
        if _guard_bdd_dict is None:
            _guard_bdd_dict = spot.make_bdd_dict()
            _guard_bdd_owner = spot.make_twa_graph(_guard_bdd_dict)
        b = spot.formula_to_bdd(or_f, _guard_bdd_dict, _guard_bdd_owner)
        return spot.bdd_to_formula(b, _guard_bdd_dict)
    except Exception:
        return or_f


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
