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

from typing import Dict, TYPE_CHECKING

from aut2ltl.result import LTLResult

if TYPE_CHECKING:
    import spot
    from aut2ltl.ltl_rewriter import Rewriter

_NAME = "deep_roundtrip"


def deep_roundtrip(rewrite: "Rewriter", *, name: str = _NAME) -> "Rewriter":
    """Build a Rewriter re-presenting the whole DAG bottom-up with `rewrite`, memoized
    on node identity (one re-presentation per distinct node). The memo is one per-call
    `dict` keyed on the `spot.formula` itself — correctness is free from the single
    hash-consed DAG (equal structure ⇒ same object ⇒ one key). An all-no-op pass returns
    the input verbatim, uncredited (the ltl_rewriter attribution rule)."""
    def run(res: LTLResult) -> LTLResult:
        formula = res.formula
        memo: Dict["spot.formula", "spot.formula"] = {}
        out = LTLResult.start(name)
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
            memo[n] = result
            return result

        rebuilt = go(formula)
        if rebuilt == formula:
            return res                                    # all no-op → no self-credit
        out.formula = rebuilt
        return out
    return run
