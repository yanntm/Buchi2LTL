"""The `Anchor` combinator Translator — the anchored SCC read-off.

`Anchor` labels the SCC `C` of the initial state of the state-based form
(`sbacc(tgba(L))`) when the component's phase is recoverable from the last
anchor letter (algorithm.md, P1 + P2), delegating every exit target to a child
translator. The label is

    Final = STAY∞ ∨ LEAVE

built by `formula.build_final` from the L/A/M/E split of `C` — stay forever
(anchored transition law under `G`, parking-aware fairness) or traverse and
exit (the law under `U`, loop-then-exit, the child label after). Exact by
construction under the precondition: no equivalence gate. One equation covers
terminal, rejecting, accepting-with-exits and single-state components alike.

A NOT_LTL exit child is absorbed and its counting family lifted back to the
initial state across an exact reaching word (`lift.exit_word`); when no exact
word exists the verdict does not lift and the peel degrades to a non-absorbing
decline.
"""

import os
import sys
from typing import Dict, List, TYPE_CHECKING

import spot

from aut2ltl.language import Language
from aut2ltl.result import LTLResult, Status
from aut2ltl.printer import format_language, format_result
from .shape import init_scc_states, lame_data, anchored_violation, reroot
from .formula import build_final
from .lift import exit_word

if TYPE_CHECKING:
    from aut2ltl.translator import Translator

_NAME = "anchor"

# ANCHOR_TRACE, or the global TRANSLATOR_TRACE_ON which lights every translator
# trace at once. Every use guards with `if _TRACE:` BEFORE building its message,
# so a formula is never flattened for a trace that will not be printed.
_TRACE = "ANCHOR_TRACE" in os.environ or "TRANSLATOR_TRACE_ON" in os.environ


def _out(res: "LTLResult") -> "LTLResult":
    """Trace the outgoing result (status / size / formula), pass it through unchanged."""
    if _TRACE:
        print("[anchor] out " + format_result(res), file=sys.stderr)
    return res


class Anchor:
    """The anchored SCC read-off as a `Translator` (`Language → LTLResult`).
    Constructed with the child labeler for exit targets; holds no state.
    Applies when the initial SCC of the state-based form is anchored (P1 + P2);
    declines otherwise."""

    name = _NAME

    def __init__(self, child: "Translator") -> None:
        self._child = child

    def __call__(self, lang: "Language") -> "LTLResult":
        aut = spot.postprocess(lang.tgba(), "sbacc")
        if _TRACE:
            print("[anchor] in " + format_language(lang, aut), file=sys.stderr)
        res = LTLResult.start(_NAME)

        # State-based generalized Büchi is what the fairness read-off transcribes;
        # sbacc(tgba) yields it by construction, so this is a guard, not a gate.
        if not aut.acc().is_generalized_buchi():
            return _out(res.fail(Status.DECLINED,
                                 "acceptance is not generalized Büchi after sbacc"))

        q0 = aut.get_init_state_number()
        C = init_scc_states(aut, q0)
        L, A, M, exits = lame_data(aut, C)
        why = anchored_violation(L, A)
        if why is not None:
            return _out(res.fail(Status.DECLINED, f"phase not anchored ({why})"))

        # Delegate each distinct exit target to Λ; credit, bail on NOK.
        dsts: List[int] = [dst for s in C for _, dst in exits[s]]
        phi: Dict[int, "spot.formula"] = {}
        for dst in dict.fromkeys(dsts):
            sub = Language.of(reroot(aut, dst))
            if _TRACE:
                print(f"[anchor] delegating exit {dst} as language: "
                      + format_language(sub, sub.tgba()), file=sys.stderr)
            child = self._child(sub)
            if child.not_ltl:
                # A NotLTL child lifts back to q0 by an EXACT reaching word
                # q0 ⟶* s →(g) dst (every step's letters restricted to fork
                # nowhere else — `lift.exit_word`), making the quotient argument
                # sound with no replay; no exact word ⇒ the verdict does not lift.
                w_dst = exit_word(aut, C, q0, dst)
                if w_dst is None:
                    return _out(res.fail(Status.DECLINED,
                        "PROBABLY_NOT_LTL -- a non-LTL residue does not lift: no "
                        "exact reaching word through the SCC (every route's "
                        "letters also enable another target), so no verdict is "
                        "asserted"))
                res.prefix(child, "; ".join(w_dst), _NAME)
                return _out(res)
            res.credit(child)
            if res.nok:
                return _out(res)
            phi[dst] = child.formula

        res.formula = build_final(aut, C, q0, L, A, M, exits, phi)
        return _out(res)
