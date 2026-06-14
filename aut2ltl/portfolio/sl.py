"""
portfolio/sl.py — the `Sl` Translator: the sl engine as a contract Translator.

`Sl` wraps aut2ltl.sl's exact self-loop / semi-linear backward labeling
(`reconstruct_ltl`) as a Translator over a `Language`. It pulls the (possibly
nondeterministic) TGBA the sl engine exploits — `Language.tgba()` — runs sl, and
simplifies on equal footing with the cascade (`_simp_f`).

Self-gating, sound BY CONSTRUCTION (not post-hoc). sl partitions each state's
outgoing edges into self-loops and exits, recurses (memoized) on the exit
targets, and assembles the language from that state by fixed rules — G(⋁self) &
GF(⋁acc) when accepting; [G(⋁self)&GF(⋁acc)] | (⋁self U ⋁exit) with exits;
(⋁self) U (⋁exit) non-accepting; ⋁(cond & X succ) for exits-only — with per-edge
downstream invariants conjoined. This is EXACT precisely on the VERY-WEAK (1-weak)
fragment (automata whose only cycles are self-loops); there the U/G/GF encoding is
the standard provably-correct translation. OFF that fragment sl DECLINES (a state
re-entered on the recursion stack, or a successor inside a genuine multi-state SCC
with no validated fragment): the engine's `UNSUPPORTED` sentinel poisons upward
and surfaces here as `LTLFormulaResult.declined`; a wrong formula is never
emitted. So soundness is BY CONSTRUCTION (exact-on-fragment + decline-otherwise),
not post-hoc checking.

The f2 (size-2 overapprox) and t2 (terminal-2-SCC) heuristics are a SEPARATE,
verify-before-use layer inside the sl engine: they PROPOSE an LTL fragment for a
2-state / terminal SCC and VALIDATE it by language equivalence before sl may use
it (a wrong guess is simply not adopted). The opt-in KR_GATE_VERIFY audit below is
CONFIRMATION of all this, not its foundation (it found zero rejections over ~170
randltl formulas).

Env knobs (the cleanup of these is a separate pass): KR_GATE_BUCHI2LTL (default
ON; =0 declines always — the pure-kr A/B), KR_GATE_MAX_STATES (skip a
pathologically large input), KR_GATE_VERIFY (opt-in audit: re-check
are_equivalent, default OFF — confirmation, not the foundation).
"""
from __future__ import annotations

import contextlib
import io
import os

import spot

from aut2ltl.contract import LTLFormulaResult, Translator
from aut2ltl.language import Language

# sl is cheap on our small explicit-letter domain; this only guards against
# handing it a pathologically large automaton.
_MAX_STATES = int(os.environ.get("KR_GATE_MAX_STATES", "60"))


class Sl:
    """The sl engine as a Translator: `Language -> LTLFormulaResult`."""

    name = "sl"

    def __call__(self, lang: Language) -> LTLFormulaResult:
        if os.environ.get("KR_GATE_BUCHI2LTL", "1") == "0":
            return LTLFormulaResult.decline()
        tgba = lang.tgba()
        if tgba.num_states() > _MAX_STATES:
            return LTLFormulaResult.decline()
        try:
            from aut2ltl.sl.reconstruction import reconstruct_ltl
            with contextlib.redirect_stdout(io.StringIO()):
                out = reconstruct_ltl(tgba)
        except Exception:
            return LTLFormulaResult.decline()
        if out.declined or out.formula is None:
            return LTLFormulaResult.decline()
        rec = out.formula
        try:
            cand = rec if isinstance(rec, spot.formula) else spot.formula(str(rec))
        except Exception:
            return LTLFormulaResult.decline()
        # sl does NOT run Spot's LTL simplifier, so its output is syntactically
        # padded; route it through `_simp_f` so it is on equal footing with the
        # cascade (language-preserving).
        try:
            from aut2ltl.kr.ltl_builders import _simp_f
            cand = _simp_f(cand)
        except Exception:
            pass
        # Opt-in soundness audit (default OFF): re-verify against the language.
        if os.environ.get("KR_GATE_VERIFY", "0") != "0":
            try:
                if not spot.are_equivalent(tgba, cand.translate()):
                    return LTLFormulaResult.decline()
            except Exception:
                return LTLFormulaResult.decline()
        return LTLFormulaResult(formula=cand, technique=set(out.technique or {self.name}))


sl: Translator = Sl()


__all__ = ["Sl", "sl"]
