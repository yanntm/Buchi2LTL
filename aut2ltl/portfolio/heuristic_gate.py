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
Spot to make it a TGBA (language-preserving).

WHAT buchi2ltl ACTUALLY IS (so this is not misread again — sl is the core, NOT
a guess-and-check heuristic):

  * `sl` (self-loop / semi-linear backward labeling, `buchi2ltl/reconstruction.py`
    `label`) is the CORE and is an EXACT state-elimination translation. For each
    state it partitions outgoing edges into self-loops and exits, recurses
    (memoized) on the exit targets, and assembles the language from that state by
    fixed rules:
        - self-loops only, accepting:        G(⋁self) & GF(⋁acc)
          (one GF per acceptance set for generalized Büchi)
        - self-loops + exits, accepting:     [G(⋁self) & GF(⋁acc)] | (⋁self U ⋁exit)
          (the stay-forever-vs-leave dichotomy)
        - non-accepting self-loops + exits:  (⋁self) U (⋁exit)
        - exits only:                        ⋁ (cond & X succ)
    with per-edge downstream invariants conjoined.
    This is EXACT precisely on the VERY-WEAK (1-weak) fragment — automata whose
    only cycles are self-loops (every nontrivial SCC is a single self-looping
    state); there the U / G / GF encoding is the standard provably-correct
    translation. OFF that fragment sl DECLINES: a state re-entered while on the
    recursion stack (`visiting`), or a successor inside a genuine multi-state SCC
    with no validated fragment (`bad_states`), yields the `UNSUPPORTED` sentinel,
    which poisons upward (any compound term containing it collapses the whole
    state). sl never emits a formula for a structure it cannot translate exactly
    — it fails loudly. So its soundness is BY CONSTRUCTION (exact-on-fragment +
    decline-otherwise), not post-hoc checking.

  * `f2` (`size2_overapprox`) and `t2` (`terminal_2scc`) are a SEPARATE,
    guess-and-check layer: they PROPOSE an LTL fragment for a 2-state / terminal
    SCC and VALIDATE it by language equivalence before sl is allowed to use it
    (injected as a pre-validated `scc_fragments[q]`). Sound because verified — a
    wrong guess is simply not adopted.

Net: the gate's adopted output is sound because sl is exact on its fragment and
f2/t2 are verify-before-use. The opt-in audit (`KR_GATE_VERIFY`, default OFF;
re-checks every adopted candidate against its node automaton and counts
`rejected`) is CONFIRMATION, not the foundation — it found ZERO rejections over
~170 randltl formulas (`fuzz_gate_decompose.py`). Combining the heuristic WITH
decomposition is the lever: decomposition exposes pieces that fall into the
very-weak sl fragment (or f2/t2), and the kr cascade carries the rest.

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


def try_heuristic_gate(aut: "spot.twa_graph", *, techniques=None) -> Optional["spot.formula"]:
    """Run the buchi2ltl heuristic on `aut`; return a hash-consed formula DAG
    for its language, or None to fall through to the kr cascade.

    Best-effort: any exception or an UNSUPPORTED/None heuristic result returns
    None. Gate KR_GATE_BUCHI2LTL (default ON; =0 restores the pure kr decompose
    path). Opt-in audit KR_GATE_VERIFY (default OFF) declines any candidate that
    is not are_equivalent to `aut` and counts it in `rejected`.

    `techniques` (optional, default None): a SET into which the adopted
    buchi2ltl technique tokens (e.g. 'sl', 't2', 'f2') are recorded for the
    portfolio report (`aut2ltl.contract.ReconResult`).
    """
    if os.environ.get("KR_GATE_BUCHI2LTL", "1") == "0":
        return None
    if aut.num_states() > _MAX_STATES:
        return None
    _STATS["tried"] += 1
    try:
        from aut2ltl.sl.reconstruction import reconstruct_ltl
        # Input is an arbitrary HOA; buchi2ltl's input form is a TGBA, so ask
        # Spot to make it one (language-preserving — the soundness step).
        tgba = spot.postprocess(aut, "TGBA", "Small", "High")
        with contextlib.redirect_stdout(io.StringIO()):
            out = reconstruct_ltl(tgba)
    except Exception:
        _STATS["errored"] += 1
        return None
    tech_tokens = out.technique
    if out.declined:       # ReconResult: "not me"
        return None
    rec = out.formula
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
        from aut2ltl.kr.ltl_builders import _simp_f
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
    if techniques is not None:
        # Record the buchi2ltl technique tokens (e.g. {"sl","t2"}).
        techniques.update(tech_tokens or {"sl"})
    return cand
