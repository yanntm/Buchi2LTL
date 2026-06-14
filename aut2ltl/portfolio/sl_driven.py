"""
portfolio/sl_driven.py — the `SlDriven` Translator: "kr under sl" (the blaster).

The mirror of the decompose gate (which is "sl under kr"). Here sl is the DRIVER:
`SlDriven(delegate)` runs aut2ltl.sl's exact self-loop backward labeling over
`Language.tgba()`, and wherever sl reaches a state it cannot translate (a
multi-state SCC) it hands the whole sub-automaton from that state to its
`delegate` Translator and reattaches the returned label. sl handles the very-weak
envelope exactly and tiny; the delegate handles the multi-cyclic core — on a
SMALLER automaton than the whole (kr's cost tracks state count, so peeling a
prefix is the structural win).

Soundness: the delegated label is L(sub) = exactly the language sl's own label(q)
would represent, so substituting a sound translator's label is interchangeable
with sl's; the surrounding (already validated) sl construction composes it
correctly (X-wrapped at the crossing edge, invariants re-added).

Termination / no ping-pong: this is the ONLY subtlety of putting `SlDriven` in a
chain, and it is now a one-line wiring rule rather than a mechanism — **`delegate`
must be a Translator that does NOT contain `SlDriven`** (a cascade-based one). On
a single strongly-connected multi-state automaton sl peels nothing and delegates
the whole; if that could route back to `SlDriven` it would loop forever. A
cascade-based delegate is a flat floor — the cascade always succeeds and never
re-enters sl — so the kr↔sl recursion shrinks to that floor and stops.
"""
from __future__ import annotations

from typing import Optional

import spot

from aut2ltl.contract import LTLFormulaResult, Translator
from aut2ltl.language import Language

__all__ = ["SlDriven"]


class SlDriven:
    """sl-driven reconstruction with delegated cores ("kr under sl"). A Translator
    over a `delegate` Translator (which must not itself contain `SlDriven`)."""

    name = "sl_driven"

    def __init__(self, delegate: Translator) -> None:
        self._delegate = delegate

    def __call__(self, lang: Language) -> LTLFormulaResult:
        from aut2ltl.sl.reconstruction import reconstruct_ltl

        deleg_tech: set = set()

        def labeler(sub: "spot.twa_graph") -> Optional["spot.formula"]:
            # Hand the multi-state core to the delegate and splice its formula DAG
            # directly (no str()): the DAG-native engine attaches it as a child
            # node WITHOUT flattening — a high-sharing core costs only its DAG.
            r = self._delegate(Language.of(sub))
            if r.declined or r.formula is None:
                return None
            deleg_tech.update(r.technique)
            return r.formula

        tgba = lang.tgba()
        try:
            out = reconstruct_ltl(tgba, scc_labeler=labeler)
        except Exception:
            return LTLFormulaResult.decline()
        if out.declined or out.formula is None:
            return LTLFormulaResult.decline()
        rec = out.formula
        try:
            cand = rec if isinstance(rec, spot.formula) else spot.formula(str(rec))
        except Exception:
            return LTLFormulaResult.decline()
        # Simplify on equal footing with the rest of the pipeline (sl skips Spot's
        # simplifier; the spliced delegate labels are already simplified).
        try:
            from aut2ltl.kr.ltl_builders import _simp_f
            cand = _simp_f(cand)
        except Exception:
            pass
        tech = set(out.technique or set()) | deleg_tech
        tech.add(self.name)
        return LTLFormulaResult(formula=cand, technique=tech)
