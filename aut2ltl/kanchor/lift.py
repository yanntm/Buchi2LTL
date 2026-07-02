"""The witness lift behind the `anchor` combinator: an exact reaching word.

When an exit child returns a NOT_LTL counting family anchored at its target
`dst`, the verdict lifts to the component's initial state only across a word
whose left quotient IS the residue past the exit (algorithm.md, "Non-LTL exit
children"). `exit_word` builds one: a path of in-`C` edges (self-loops skipped)
from `q0` to a state carrying an exit into `dst`, then that exit guard — with
every step's guard restricted to the letters enabling no edge to a different
target from its source, so the word has a single continuation at each step.
The restriction subtracts all other-target edges, self-loops included, so the
shared loop letters an anchored component allows are excluded per step;
parallel edges to the same target are harmless (finite-prefix marks never
touch an `Inf` acceptance set).
"""

from typing import Dict, List, Optional, Set, Tuple

import spot
import buddy

__all__ = ["exit_word"]


def exit_word(
    aut: "spot.twa_graph", C: Set[int], q0: int, dst: int
) -> Optional[List[str]]:
    """An exact word traversing `C` from `q0` to an exit into `dst`, as
    Spot-syntax letter strings, or `None` when no exact route exists (every
    route's guards fully overlap edges to other targets — the verdict must not
    lift then)."""
    d = aut.get_dict()

    def lit(cond: "buddy.bdd") -> str:
        return str(spot.bdd_to_formula(cond, d))

    def exact(cond: "buddy.bdd", src: int, target: int) -> "buddy.bdd":
        """`cond` minus every out-guard of `src` leading elsewhere than `target`."""
        for c, dd in [(e.cond, e.dst) for e in aut.out(src)]:
            if dd != target:
                cond = cond & buddy.bdd_not(c)
        return cond

    prev: Dict[int, Tuple[int, str]] = {}   # state -> (parent, exact guard reaching it)
    seen = {q0}
    queue = [q0]
    qi = 0
    while qi < len(queue):
        p = queue[qi]
        qi += 1
        for e in aut.out(p):                 # an exit p →(g) dst ends the word
            if e.dst == dst:
                g = exact(e.cond, p, dst)
                if g == buddy.bddfalse:
                    continue                 # this exit's letters all fork; try another
                word: List[str] = []
                cur = p
                while cur != q0:
                    parent, guard = prev[cur]
                    word.append(guard)
                    cur = parent
                word.reverse()
                return word + [lit(g)]
        for e in aut.out(p):                 # else walk on through C (no self-loops)
            if e.dst in C and e.dst != p and e.dst not in seen:
                g = exact(e.cond, p, e.dst)
                if g == buddy.bddfalse:
                    continue                 # no exact letter for this step
                seen.add(e.dst)
                prev[e.dst] = (p, lit(g))
                queue.append(e.dst)
    return None
