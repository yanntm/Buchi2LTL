"""
bls/operators/support.py — non-recursive support for the reachability operators.

The five reachability formulas (reach / wreach / solid / wsolid / dashed) are mutually
recursive and live one per file; everything they SHARE that is not itself recursive
lives here:
  - the native spot.formula builders, re-exported under their short names;
  - tracing (KR_TRACE) and the runaway guard (KR_REACH_GUARD);
  - the per-build memo decorator for the solid/dashed helpers;
  - the combined-letter enumeration (Enter/Stay/Leave primitives) and letter fusion.

Depends only on `aut2ltl.ltl.builders`; imports none of the operator modules, so it is
the DAG floor beneath the recursive layer.
"""

from __future__ import annotations
from typing import List, Tuple
import functools
import os

# Guard helpers, simplification, and native spot.formula builders live in
# aut2ltl/ltl/builders.py (no kr deps). Re-exported here under their short names so
# the operator modules import them from one place.
from aut2ltl.ltl.builders import (
    letters_to_prop,
    make_guard,
    simplify_ltl,
    normalize_ltl,
    _normalize_ltl,
    _tt, _ff, _ap, _And, _Or, _Not, _X, _U,
    _to_f, _letters_to_f, _str_f, _short_f, _simp_f, _fuse_or,
)

# Tracing (enable with KR_TRACE=1): verbose level-by-level construction traces.
TRACE_ON = os.getenv("KR_TRACE", "0").lower() in ("1", "true", "yes", "on")

# Runaway guard on DISTINCT reach subproblems (holder.reach_calls = memo misses,
# not raw calls). Legitimate big builds stay finite; an infinite same-level
# recursion grows without bound and still trips it. Wall-clock budgets belong to
# the callers.
REACH_GUARD = int(os.getenv("KR_REACH_GUARD", "5000000"))

# --- per-build memo decorator + tracing -------------------------------------
def _memo_reach_helper(tag: str):
    """Memoize a helper on the CascadeHolder's `helper_memo` (per build; `casc` is the
    holder), keyed by `(tag, S, B, beta, T, tau, level)`. `beta`/`tau` are normalized to
    hash-consed spot.formula before keying, so the `str` and `formula` spellings of a
    guard share an entry. The helpers fan in heavily (the same subproblem is reached
    along many call paths), so this memo is what keeps the mutually-recursive expansion a
    DAG build rather than a tree blow-up. One entry per distinct key; fresh per holder."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(S, B, beta, T, tau, casc, level=0):
            beta_f = _ff() if beta is None else _to_f(beta)
            tau_f = _tt() if tau is None else _to_f(tau)
            key = (tag, S, B, beta_f, T, tau_f, level)
            memo = casc.helper_memo
            hit = memo.get(key)
            if hit is None:
                hit = fn(S, B, beta_f, T, tau_f, casc, level)
                memo[key] = hit
            return hit
        return wrapper
    return deco

def _trace(msg: str) -> None:
    if TRACE_ON:
        print("[KR] " + msg)

# --- combined-letter enumeration (Enter/Stay/Leave) + letter fusion ---------
def _combined_letters_at_level(casc: "Cascade", level: int) -> List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]]:
    """Observable combined letters at layer `level`: list of (li, pre, arrived)
    over every h-image config `pre` and letter li. The paper's combined letter
    ⟨σ, L⟩ for this layer corresponds to (li, pre[level+1:]); pre[level] is the
    layer state it is observed from. Enumerating h-image configs is the
    observable approximation of the full product cascade (exact when h covers
    the reachable configs, which decompose_aut's state_to_config provides).
    """
    out: List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]] = []
    for pre in casc.all_configs():
        if len(pre) <= level:
            continue
        for li in range(casc.num_letters()):
            try:
                arr = casc.move_config(pre, li)
            except Exception:
                continue
            if li >= len(casc.letter_valuations):
                continue
            out.append((li, pre, arr))
    return out


def _dedupe(
    triples: List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]],
    level: int,
) -> List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]]:
    """Collapse triples by the paper's combined-letter identity `(letter, lower-config
    suffix)` — the observable enumeration can present the same combined letter from
    several configs; the first occurrence is the structural representative."""
    seen: dict = {}
    for li, pre, arr in triples:
        key = (li, pre[level + 1:])
        if key not in seen:
            seen[key] = (li, pre, arr)
    return list(seen.values())


# Letter fusion (dag_folding.md counter-measure B): at every enumeration
# site the summand reads the letter ONLY through its guard, so letters with
# an equal group key are fused into one summand whose guard is the
# Minato-minimized OR. KR_FUSE_LETTERS=0 restores the per-letter literal
# paper shape (grounding comparisons).
_FUSE_LETTERS = os.getenv("KR_FUSE_LETTERS", "1").lower() not in ("0", "false", "no", "off")


def _fuse_letters(
    triples: List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]],
    casc: "Cascade",
    level: int,
    with_arr: bool = False,
) -> List[Tuple["spot.formula", Tuple[int, ...], Tuple[int, ...]]]:
    """Group (li, pre, arr) triples whose summand is identical up to the
    guard. Key = the _dedupe key minus li (pre suffix; + arr when the
    summand reads the arrival — enter_t/enter_b). Returns
    [(fused_guard, pre, arr)] with the first triple of each group as the
    structural representative (same convention as _dedupe). Soundness:
    dag_folding.md "Letter fusion"."""
    groups: dict = {}
    for li, pre, arr in triples:
        g_f = _letters_to_f(casc.letter_valuations[li], casc.aps)
        if g_f.is_ff():
            continue
        key: tuple = (pre[level + 1:], arr) if with_arr else pre[level + 1:]
        if not _FUSE_LETTERS:
            key = (li, key)
        ent = groups.get(key)
        if ent is None:
            groups[key] = ([g_f], pre, arr)
        else:
            ent[0].append(g_f)
    return [(_fuse_or(gs), pre, arr) for (gs, pre, arr) in groups.values()]
