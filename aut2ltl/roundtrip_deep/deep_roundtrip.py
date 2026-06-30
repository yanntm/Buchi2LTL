"""The `deep_roundtrip` Rewriter (see algorithm.md).

`deep_roundtrip(R)` re-presents EVERY node of the formula DAG bottom-up: rewrite a
node's children first, rebuild the node from the re-presented children, then re-present
that rebuilt node with the Rewriter `R`. One post-order pass over the hash-consed DAG,
memoized on node identity — so each distinct node is re-presented once (DAG-complexity),
and a child's reduction is visible to its parent in the SAME pass. That is the lever:
shrinking a child can drop its parent under the translate bound, so the parent becomes
re-presentable in turn and a tower collapses from the leaves up.

No finder and no cut node (unlike `roundtrip` / `roundtrip_decomp`): the descent IS the
search. `R` carries its own never-regress floor (e.g. `best_of([identity, relabel(Λ)])`),
so a node is only ever replaced by an equivalent no-larger form, and a declined
re-presentation keeps the rebuilt node — the pass never regresses or declines.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, TYPE_CHECKING

from aut2ltl.result import LTLResult
from aut2ltl.printer import format_result
from aut2ltl.ltl.metrics import dag_metrics

if TYPE_CHECKING:
    import spot
    from aut2ltl.ltl_rewriter import Rewriter

_NAME = "deep_roundtrip"

# On when either DEEP_ROUNDTRIP_TRACE or the global TRANSLATOR_TRACE_ON is set
# (presence; value ignored). Built only inside `if _TRACE:`, so nothing is computed
# when off. Shows the incoming/outgoing result and each node the bottom-up pass
# actually re-presents (where a tower collapses from the leaves up).
_TRACE = "DEEP_ROUNDTRIP_TRACE" in os.environ or "TRANSLATOR_TRACE_ON" in os.environ


class DeepRoundtrip:
    """A Rewriter re-presenting the whole formula DAG bottom-up with a child Rewriter,
    memoized on node identity (one re-presentation per distinct node). The memo is a
    per-call dict keyed on the `spot.formula` itself (equal structure ⇒ same object ⇒
    one key). An all-no-op pass returns the input verbatim, uncredited. A named
    functor."""

    def __init__(self, rewrite: "Rewriter", name: str = _NAME) -> None:
        self._rewrite = rewrite
        self.name = name

    def __call__(self, res: LTLResult) -> LTLResult:
        rewrite = self._rewrite
        formula = res.formula
        if _TRACE:
            print("[deep_roundtrip] in " + format_result(res), file=sys.stderr)
        memo: Dict["spot.formula", "spot.formula"] = {}
        out = LTLResult.start(self.name)
        out.credit(res)

        def go(n: "spot.formula") -> "spot.formula":
            cached = memo.get(n)
            if cached is not None:
                return cached
            rebuilt = n.map(go)                          # children first (bottom-up)
            r = rewrite(LTLResult.success(rebuilt))       # re-present the rebuilt node
            if r.ok:
                out.credit(r)
                result = r.formula
            else:
                result = rebuilt                          # decline → keep rebuilt, don't taint out
            if _TRACE and result != rebuilt:
                mb, ma = dag_metrics(rebuilt), dag_metrics(result)
                print(f"[deep_roundtrip]   node re-presented: dag {mb.dag_nodes}->"
                      f"{ma.dag_nodes} tree {mb.tree_nodes}->{ma.tree_nodes}",
                      file=sys.stderr)
            memo[n] = result
            return result

        rebuilt = go(formula)
        if rebuilt == formula:
            if _TRACE:
                print("[deep_roundtrip] out no-op (input unchanged)", file=sys.stderr)
            return res                                    # all no-op → no self-credit
        out.formula = rebuilt
        if _TRACE:
            print("[deep_roundtrip] out " + format_result(out), file=sys.stderr)
        return out


def deep_roundtrip(rewrite: "Rewriter", *, name: str = _NAME) -> "Rewriter":
    """The `DeepRoundtrip` functor over `rewrite`."""
    return DeepRoundtrip(rewrite, name)
