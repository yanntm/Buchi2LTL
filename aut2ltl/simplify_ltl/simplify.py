"""The `Simplify` Translator decorator (see README.md).

`Simplify(child, level)` wraps any Translator: forward the Language to `child`, and
on an OK result replace its formula with a language-preserving simplification at the
chosen level — `'lo'` our DAG-size-aware rules (`own_simplify`), `'hi'` those plus
Spot's `tl_simplifier` (`_simp_f`). A declined / NOT_LTL result passes through
unchanged; the technique tags stay the child's (simplification is representation, not
a reconstruction method, so it stamps no tag of its own).
"""

from __future__ import annotations

import os
import sys
from typing import Callable, TYPE_CHECKING

from aut2ltl.ltl.builders import own_simplify, _simp_f
from aut2ltl.result import LTLResult

if TYPE_CHECKING:
    import spot

    from aut2ltl.translator import Translator
    from aut2ltl.language import Language

# On when SIMPLIFY_TRACE or the global TRANSLATOR_TRACE_ON is set (presence). Built
# only inside `if _TRACE:`. Simplification is NOT neutral — 'hi' runs Spot's
# tl_simplifier, which can rewrite structure (e.g. drop a leading X), silently and
# in place. Trace every change it makes, so the new form is attributed here rather
# than to whichever brick happened to print last.
_TRACE = "SIMPLIFY_TRACE" in os.environ or "TRANSLATOR_TRACE_ON" in os.environ

# level → the simplifier it applies. 'lo' is our own DAG rules; 'hi' also runs Spot's
# tl_simplifier after ours (both, to a fixpoint).
_LEVELS: "dict[str, Callable[[spot.formula], spot.formula]]" = {
    "lo": own_simplify,
    "hi": _simp_f,
}


class Simplify:
    """Simplify a child Translator's formula. `level` in {'lo','hi'}: 'lo' = our DAG
    rules only; 'hi' = our rules then Spot's LTL simplifier. Transparent otherwise —
    a NOK result and the child's technique tags pass through unchanged."""

    name = "simplify"

    def __init__(self, child: "Translator", level: str = "lo") -> None:
        if level not in _LEVELS:
            raise ValueError(f"level must be 'lo' or 'hi', got {level!r}")
        self._child = child
        self._level = level
        self._simp = _LEVELS[level]

    def __call__(self, lang: "Language") -> "LTLResult":
        res = self._child(lang)
        if not res.ok:
            return res                                   # NOK: pass through untouched
        before = res.formula
        after = self._simp(before)
        if after == before:
            return res                                   # no-op: the child's result, untouched
        if _TRACE:
            from aut2ltl.ltl.metrics import dag_metrics       # deferred: keep floor acyclic
            from aut2ltl.ltl.printers import format_gated
            mb, ma = dag_metrics(before), dag_metrics(after)
            print(f"[simplify:{self._level}] dag {mb.dag_nodes}->{ma.dag_nodes}  "
                  f"{format_gated(before, limit=400)}  ==>  "
                  f"{format_gated(after, limit=400)}", file=sys.stderr)
        # A NEW result carrying the simplified formula — NEVER mutate `res`, which a
        # caller (e.g. a best_of incumbent) may still hold. Credit the child's
        # provenance; stamp no tag of our own (simplification is representation, not a
        # reconstruction method).
        out = LTLResult.start()
        out.credit(res)
        out.formula = after
        return out
