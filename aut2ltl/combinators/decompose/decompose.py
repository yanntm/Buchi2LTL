"""aut2ltl/decomp/decompose.py — the shared decomposition combinator.

The three decomposers (strength / acceptance / scc) are ONE shape: split the language
into strictly-smaller pieces, label each the SAME way (recursion), recombine the parts
under a logical connective — differing only in (split, connective, tag). This factors
that shape into `decompose(split, connective, tag)`: `recurse` (the fixpoint) wrapping
a `combine` that is the result composition-monoid (`fuse`) finished with a root ∧/∨.
Each decomposer is then a one-liner over its own `split`. (`inv` is the clean
`Decorator` that does NOT fit this shape — it has no split.) The recurse body here is a
*combine* (`∧/∨` over all pieces); contrast daisy, whose recurse body is a *choice*
(`⊕`, try-peel-else-floor) — same `fix`, different body operation.
"""
from __future__ import annotations

import os
import sys
from typing import Callable, List, TYPE_CHECKING

import spot

from aut2ltl.language import Language
from aut2ltl.combinators.recurse import recurse
from aut2ltl.result import LTLResult, fuse
from aut2ltl.printer import format_language, format_result
from aut2ltl.ltl.builders import own_simplify
from aut2ltl.verifier import revalidated_by_parts

if TYPE_CHECKING:
    from aut2ltl.translator import Translator, Decorator

# On when either DECOMP_TRACE or the global TRANSLATOR_TRACE_ON is set (presence;
# value ignored). Built only inside `if _TRACE:`, so nothing is computed when off.
# Makes the split and the per-operand dispatch (input language, each operand, its
# result) visible — one flag for all three decomposers (they share this combinator).
_TRACE = "DECOMP_TRACE" in os.environ or "TRANSLATOR_TRACE_ON" in os.environ

# Fold a list of formulas into one (e.g. `spot.formula.Or` / `spot.formula.And`).
Connective = Callable[[List["spot.formula"]], "spot.formula"]
# Return the strictly-smaller sub-automata to recurse on, or `[]` for "no split".
Split = Callable[["Language"], List["spot.twa_graph"]]


def combine(connective: "Connective", tag: str, parts: List["LTLResult"]) -> "LTLResult":
    """Recombine per-part results under `connective` via the accumulate idiom: seed an
    OK result tagged `<tag><k>`, credit each part (worst status wins, diagnoses
    accumulate), bail if NOK — a declined part declines the whole. On OK, own-simplify
    the parts and their connective (a node no per-part pass saw whole)."""
    res = fuse(LTLResult.start(f"{tag}{len(parts)}"), *parts)
    if res.nok:
        return res
    forms = [own_simplify(p.formula) for p in parts]
    res.formula = own_simplify(connective(forms))
    return res


def decompose(split: "Split", connective: "Connective", tag: str) -> "Decorator":
    """The shared decomposition shape as a `Decorator` (`leaf -> Translator`): split the
    language; if it splits, recurse on each strictly-smaller piece and `combine` the
    parts under `connective`; else delegate the whole language to `leaf`. `recurse` ties
    the knot (each piece is labelled the same way); termination rests on `split` handing
    back strictly-smaller pieces. Sound by construction (every part is faithful-or-NOK).
    Adds `<tag><k>` to the technique and forwards the parts' techniques (via `combine`)."""
    # The empty fold identifies the connective (`And([]) = tt`, `Or([]) = ff`) —
    # which is also how the parts-replay combines memberships (∧ → all, ∨ → any).
    conjunctive = bool(connective([]).is_tt())

    def builder(leaf: "Translator") -> "Translator":
        def step(self: "Translator") -> "Translator":
            def run(lang: "Language") -> "LTLResult":
                pieces = split(lang)
                if not pieces:
                    if _TRACE:
                        print(f"[{tag}] in {format_language(lang, lang.tgba())}"
                              " -> no split, delegate to leaf", file=sys.stderr)
                    return leaf(lang)
                if _TRACE:
                    print(f"[{tag}] in {format_language(lang, lang.tgba())}"
                          f" -> split into {len(pieces)} operands", file=sys.stderr)
                subs: List["Language"] = []
                parts: List["LTLResult"] = []
                for k, p in enumerate(pieces):
                    sub = Language.of(p)
                    subs.append(sub)
                    if _TRACE:
                        print(f"[{tag}]   operand {k + 1}/{len(pieces)} "
                              + format_language(sub, sub.tgba()), file=sys.stderr)
                    r = self(sub)
                    if _TRACE:
                        print(f"[{tag}]   operand {k + 1}/{len(pieces)} -> "
                              + format_result(r), file=sys.stderr)
                    parts.append(r)
                # A part's NOT_LTL is a verdict about the PART's language, and
                # non-LTL-ness survives neither connective: keep it only if its
                # family replays against THIS level's language — queried through
                # the parts, whose connective the host's membership IS (the split
                # is faithful) — else degrade to a non-absorbing decline (see
                # algorithm.md, The NOT_LTL crossing).
                res = revalidated_by_parts(combine(connective, tag, parts),
                                           subs, conjunctive)
                if _TRACE:
                    print(f"[{tag}] out " + format_result(res), file=sys.stderr)
                return res
            return run
        return recurse(step, name=tag)
    return builder
