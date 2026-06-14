"""
kr/decompose_recombine.py — root-level decompose-and-recombine front end.

ORTHOGONAL to the rest of kr/: this module only *consumes* the existing
`decompose_aut` + `reconstruct_ltl_paper_style` on acceptance-trivial pieces and
recombines their formula DAGs with a root boolean operator. Nothing in the core
imports this; it is a wrapper you call instead of the monolithic path.

Soundness (kr is language-faithful, a ROOT boolean op is a pure position-0
language op — no temporal-placement / acceptance-coupling caveats):

  * AND by acceptance set.  On a DETERMINISTIC automaton every word has one run,
    so for conjunctive acceptance  acc = ⋀ᵢ cᵢ:
        L(A) = ⋂ᵢ L(A | acc:=cᵢ)        (shared run -> exact)
    Split the acceptance condition by top_conjuncts(), run kr on each
    single-condition piece, recombine with ⋀.  Determinism is REQUIRED here
    (on a nondeterministic automaton ⋂L(Aᵢ) ⊋ L(A)).

  * OR by strength.  Spot's strength decomposition splits an automaton into
    weak / terminal / strong sub-automata whose UNION is the language
    (Renault et al., TACAS'13; exact for any automaton):
        L(A) = ⋃ₖ L(decompose_scc(A,k))
    Run kr on each piece, recombine with ⋁.

Dispatch is keyed on the shape of the deterministic acceptance condition:
conjunctive -> AND; else multi-strength -> OR; else the monolithic kr.

The two splits collapse the Muller DNF out of the Fin web up to the root: each
piece has a singleton good set, so its census is small.  See kr/STATUS.md
("decompose-and-recombine") and kr/TODO.md P1.
"""
from __future__ import annotations

import os
from typing import Callable, List, Tuple

import spot

from .gap_bridge import decompose_aut
from .heuristic_gate import try_heuristic_gate
from .reachability import reconstruct_ltl_paper_style
from .recon_result import ReconResult

__all__ = ["reconstruct_decomposed", "split_report"]

# kr's census is acutely sensitive to the input STATE COUNT (it sets the cascade
# depth), so we state-minimize the determinized automaton before splitting. SAT
# minimization is state-optimal for a fixed acceptance but exponential, so it is
# gated to small automata (our domain — explicit 2^|AP| letters, few states).
_SAT_MIN_STATES = int(os.environ.get("KR_SAT_MIN_STATES", "30"))

# A reconstruct function: Cascade -> spot.formula.
ReconstructFn = Callable[..., "spot.formula"]


def _to_split_form(aut: "spot.twa_graph") -> "spot.twa_graph":
    """Deterministic, STATE-MINIMAL automaton in GENERIC acceptance — keeps the
    generalized Büchi (⋀Inf) / Streett conjunctive shape instead of collapsing
    to parity. Determinism is the soundness precondition for the AND split.

    AUTOMATON-ONLY (the kr input contract is an automaton/HOA, never an LTL
    formula). State count matters: kr's census is acutely sensitive to it (it
    sets the cascade depth), and `postprocess(det,generic)` can leave a
    non-minimal automaton whose pieces then explode (e.g. `GFa&FGb`: 2-state
    postprocess -> recombined tree 9.5e15). SAT minimization is state-optimal
    for the fixed acceptance and recovers the minimal form (1 state -> tree
    313), purely on the automaton. Gated to small automata (SAT is
    exponential); best-effort.
    """
    det = spot.postprocess(aut, "deterministic", "generic")
    if det.num_states() <= _SAT_MIN_STATES:
        try:
            m = spot.sat_minimize(det)
            if m is not None and m.num_states() < det.num_states():
                det = m
        except Exception:
            pass
    return det


def _and_pieces(aut: "spot.twa_graph") -> List["spot.twa_graph"]:
    """One single-condition sub-automaton per top-level acceptance conjunct.
    Empty/singleton list means 'not a conjunction' (no AND split)."""
    conj = aut.acc().get_acceptance().top_conjuncts()
    if len(conj) < 2:
        return []
    pieces = []
    for c in conj:
        sub = spot.automaton(aut.to_str("hoa"))  # independent clone
        sub.set_acceptance(spot.acc_cond(aut.num_sets(), c))
        spot.cleanup_acceptance_here(sub)
        pieces.append(sub)
    return pieces


def _or_pieces(aut: "spot.twa_graph") -> List["spot.twa_graph"]:
    """Strength decomposition: weak / terminal / strong sub-automata whose union
    is the language. Returns [] when the automaton is single-strength (the
    decomposition would just return the whole automaton)."""
    si = spot.scc_info(aut)
    pieces = []
    for keep in ("w", "t", "s"):
        try:
            sub = spot.decompose_scc(si, keep)
        except Exception:
            sub = None
        if sub is not None and sub.num_states() > 0:
            pieces.append(sub)
    # A genuine split needs at least two strengths present.
    return pieces if len(pieces) >= 2 else []


def _base(aut, reconstruct, decompose_kwargs, techniques) -> "spot.formula":
    """Acceptance-trivial piece -> existing monolithic kr."""
    casc = decompose_aut(aut, **decompose_kwargs)
    # The leaf method tag is knowable only INSIDE reconstruct_ltl_paper_style,
    # so thread the accumulator into the default reconstruct. Custom reconstructs
    # (probe stubs) don't take it; record a generic 'base' for them.
    if reconstruct is reconstruct_ltl_paper_style:
        return reconstruct(casc, techniques=techniques)
    phi = reconstruct(casc)
    if techniques is not None:
        techniques.add("base")
    return phi


def _dispatch(aut, reconstruct, decompose_kwargs, depth, max_depth, techniques) -> "spot.formula":
    # Gate placement vs decomposition. KR_GATE_UNDER_DECOMP (default ON): the
    # buchi2ltl gate goes UNDER decomposition — split FIRST, gate only the
    # leaves that no longer split (so a decomposable input is always cut into
    # pieces, even when the gate could take it whole; we then gate each piece).
    # =0 restores the old order (gate first at every node, short-circuiting the
    # split). SOUND either way: a ROOT boolean op is a position-0 language op and
    # the gate is sound-by-construction (kr/heuristic_gate.py).
    under_decomp = os.environ.get("KR_GATE_UNDER_DECOMP", "1") != "0"

    if not under_decomp:
        phi = try_heuristic_gate(aut, techniques=techniques)
        if phi is not None:
            return phi
    if depth < max_depth:
        and_p = _and_pieces(aut)
        if and_p:
            if techniques is not None:
                techniques.add(f"and{len(and_p)}")
            return spot.formula.And(
                [_dispatch(p, reconstruct, decompose_kwargs, depth + 1, max_depth, techniques)
                 for p in and_p]
            )
        or_p = _or_pieces(aut)
        if or_p:
            if techniques is not None:
                techniques.add(f"or{len(or_p)}")
            return spot.formula.Or(
                [_dispatch(p, reconstruct, decompose_kwargs, depth + 1, max_depth, techniques)
                 for p in or_p]
            )
    # Leaf (no further split): gate now (if not already tried), else the cascade.
    if under_decomp:
        phi = try_heuristic_gate(aut, techniques=techniques)
        if phi is not None:
            return phi
    return _base(aut, reconstruct, decompose_kwargs, techniques)


def reconstruct_decomposed(
    aut: "spot.twa_graph",
    *,
    reconstruct: ReconstructFn = reconstruct_ltl_paper_style,
    max_depth: int = 4,
    gap_cmd: str = "gap",
    timeout: int = 180,
    max_aps: int = 5,
) -> ReconResult:
    """Root decompose-and-recombine: deterministic-generic state-minimal
    normalize, split the acceptance condition (AND by conjunct / OR by
    strength), run the existing kr on each acceptance-trivial piece, recombine
    with the root ⋀/⋁.

    `aut` is an automaton (the kr input contract — HOA, never an LTL formula).
    Returns a `ReconResult` (`.formula` is the hash-consed spot.formula DAG;
    `.technique` is the set of methods that contributed). Falls through to the
    monolithic kr when no split applies.
    """
    decompose_kwargs = dict(gap_cmd=gap_cmd, timeout=timeout, max_aps=max_aps)
    techniques: set = set()
    under_decomp = os.environ.get("KR_GATE_UNDER_DECOMP", "1") != "0"

    if not under_decomp:
        # OLD order: gate on the RAW input first, preempting decomposition.
        phi = try_heuristic_gate(aut, techniques=techniques)
        if phi is not None:
            return ReconResult(phi, techniques)
        det = _to_split_form(aut)
        phi = _dispatch(det, reconstruct, decompose_kwargs, 0, max_depth, techniques)
        return ReconResult(phi, techniques)

    # NEW (default): decomposition takes precedence over the gate. But if the
    # ROOT does not split, gate the RAW (pre-determinization) input — buchi2ltl's
    # backward labeling exploits the nondeterministic translate-style TGBA, which
    # `_to_split_form`'s determinization can destroy (e.g. coBüchi FGa|FGb). So
    # the raw-form advantage is kept exactly for the non-decomposable inputs.
    det = _to_split_form(aut)
    if not (_and_pieces(det) or _or_pieces(det)):
        phi = try_heuristic_gate(aut, techniques=techniques)
        if phi is not None:
            return ReconResult(phi, techniques)
    phi = _dispatch(det, reconstruct, decompose_kwargs, 0, max_depth, techniques)
    return ReconResult(phi, techniques)


def split_report(aut: "spot.twa_graph") -> Tuple[str, int]:
    """Diagnose how the root would split this automaton (no reconstruction).
    Returns (kind, n_pieces): kind in {'and','or','none'}."""
    det = _to_split_form(aut)
    and_p = _and_pieces(det)
    if and_p:
        return ("and", len(and_p))
    or_p = _or_pieces(det)
    if or_p:
        return ("or", len(or_p))
    return ("none", 1)
