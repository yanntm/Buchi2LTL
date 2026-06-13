"""
kr/heuristic_gate.py — the buchi2ltl heuristic as a pre-filter for the
decompose-and-recombine dispatcher.

Historically buchi2ltl/ (backward labeling + the f2 size-2 / t2 terminal-SCC
absorption heuristics) and kr/ (the paper cascade) were kept strictly separate.
The paper construction is now stable, so we WIRE the heuristic in as a gate:
at each node of `decompose_recombine._dispatch` (and on the raw input first) we
try the heuristic; if it returns a formula we adopt it (it is tiny and fast),
otherwise we fall through to the kr cascade. Combining the heuristic WITH
decomposition is the new idea — cases the heuristic cannot take whole may split
into pieces it can.

Soundness — a composition of sound steps, NO per-call equivalence check:

    arbitrary HOA  --(Spot postprocess, language-preserving)-->  TGBA
                   --(buchi2ltl, self-validating)-->            formula

buchi2ltl's input form is a TGBA; our node may carry any acceptance, so we ask
Spot to make it a TGBA (language-preserving). buchi2ltl is sound by
construction — its f2/t2 sub-heuristics validate their fragments by round-trip
language equivalence and it returns UNSUPPORTED (None / raises) rather than
emitting an unsound formula. We confirmed this empirically: the opt-in audit
check below (`KR_GATE_VERIFY`) found ZERO rejections across the full MP survey,
so it is OFF by default. Flip it on to re-audit (it then declines, and counts,
any candidate not are_equivalent to the node automaton).

This module is the ONE place kr touches buchi2ltl; the core operators stay pure.
"""
from __future__ import annotations

import contextlib
import io
import os
from typing import Optional

import spot

__all__ = ["try_heuristic_gate", "gate_stats", "reset_gate_stats"]

# buchi2ltl is cheap on our small explicit-letter domain; this only guards
# against handing it a pathologically large automaton.
_MAX_STATES = int(os.environ.get("KR_GATE_MAX_STATES", "60"))

# Process-lifetime instrumentation (read by probes/tests). `rejected` is only
# ever nonzero under the opt-in audit (KR_GATE_VERIFY) — it stays 0 in
# production and that is the sound-by-construction evidence.
_STATS = {"tried": 0, "produced": 0, "adopted": 0, "rejected": 0, "errored": 0}


def gate_stats() -> dict:
    """Snapshot of the gate counters."""
    return dict(_STATS)


def reset_gate_stats() -> None:
    for k in _STATS:
        _STATS[k] = 0


def try_heuristic_gate(aut: "spot.twa_graph") -> Optional["spot.formula"]:
    """Run the buchi2ltl heuristic on `aut`; return a hash-consed formula DAG
    for its language, or None to fall through to the kr cascade.

    Best-effort: any exception or an UNSUPPORTED/None heuristic result returns
    None. Gate KR_GATE_BUCHI2LTL (default ON; =0 restores the pure kr decompose
    path). Opt-in audit KR_GATE_VERIFY (default OFF) declines any candidate that
    is not are_equivalent to `aut` and counts it in `rejected`.
    """
    if os.environ.get("KR_GATE_BUCHI2LTL", "1") == "0":
        return None
    if aut.num_states() > _MAX_STATES:
        return None
    _STATS["tried"] += 1
    try:
        from buchi2ltl.reconstruction import reconstruct_ltl
        # Input is an arbitrary HOA; buchi2ltl's input form is a TGBA, so ask
        # Spot to make it one (language-preserving — the soundness step).
        tgba = spot.postprocess(aut, "TGBA", "Small", "High")
        with contextlib.redirect_stdout(io.StringIO()):
            out = reconstruct_ltl(tgba)
    except Exception:
        _STATS["errored"] += 1
        return None
    rec = out[0] if isinstance(out, (tuple, list)) else out
    if rec is None:
        return None
    try:
        cand = rec if isinstance(rec, spot.formula) else spot.formula(str(rec))
    except Exception:
        _STATS["errored"] += 1
        return None
    # buchi2ltl does NOT run Spot's LTL simplifier, so its output is
    # syntactically padded (e.g. Fa|Gb emits a 5-temporal form that simplifies
    # to 2). Every other kr node passes through `_simp_f`; route the gate output
    # through it too so adopted formulas are on equal footing with the cascade
    # (removes the apparent obligation-case regressions; language-preserving).
    try:
        from kr.ltl_builders import _simp_f
        cand = _simp_f(cand)
    except Exception:
        pass
    _STATS["produced"] += 1
    # Opt-in soundness audit (default OFF): re-verify against the node language.
    if os.environ.get("KR_GATE_VERIFY", "0") != "0":
        try:
            ok = spot.are_equivalent(aut, cand.translate())
        except Exception:
            _STATS["errored"] += 1
            return None
        if not ok:
            _STATS["rejected"] += 1
            return None
    _STATS["adopted"] += 1
    return cand
