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


def _base(aut, reconstruct, decompose_kwargs) -> "spot.formula":
    """Acceptance-trivial piece -> existing monolithic kr."""
    casc = decompose_aut(aut, **decompose_kwargs)
    return reconstruct(casc)


def _dispatch(aut, reconstruct, decompose_kwargs, depth, max_depth) -> "spot.formula":
    # buchi2ltl heuristic gate, tried FIRST at every node (top + each piece):
    # a tiny heuristic formula short-circuits the cascade. Declining nodes still
    # split below, so the heuristic also sees the pieces — the whole point of
    # combining it WITH decomposition. SOUND by composition: Spot makes the node
    # a TGBA (language-preserving) and buchi2ltl is sound-by-construction
    # (kr/heuristic_gate.py). Gate KR_GATE_BUCHI2LTL (default ON).
    phi = try_heuristic_gate(aut)
    if phi is not None:
        return phi
    if depth < max_depth:
        and_p = _and_pieces(aut)
        if and_p:
            return spot.formula.And(
                [_dispatch(p, reconstruct, decompose_kwargs, depth + 1, max_depth)
                 for p in and_p]
            )
        or_p = _or_pieces(aut)
        if or_p:
            return spot.formula.Or(
                [_dispatch(p, reconstruct, decompose_kwargs, depth + 1, max_depth)
                 for p in or_p]
            )
    return _base(aut, reconstruct, decompose_kwargs)


def reconstruct_decomposed(
    aut: "spot.twa_graph",
    *,
    reconstruct: ReconstructFn = reconstruct_ltl_paper_style,
    max_depth: int = 4,
    gap_cmd: str = "gap",
    timeout: int = 180,
    max_aps: int = 5,
) -> "spot.formula":
    """Root decompose-and-recombine: deterministic-generic state-minimal
    normalize, split the acceptance condition (AND by conjunct / OR by
    strength), run the existing kr on each acceptance-trivial piece, recombine
    with the root ⋀/⋁.

    `aut` is an automaton (the kr input contract — HOA, never an LTL formula).
    Returns a hash-consed spot.formula DAG (same contract as reconstruct_*).
    Falls through to the monolithic kr when no split applies.
    """
    decompose_kwargs = dict(gap_cmd=gap_cmd, timeout=timeout, max_aps=max_aps)
    # Heuristic gate on the RAW input first: buchi2ltl's backward-labeling
    # heuristics exploit the (often nondeterministic) translate-style TGBA
    # structure, which `_to_split_form`'s determinization destroys — e.g.
    # determinized coBüchi (FGa|FGb) defeats the heuristic, while the raw form
    # does not. Sound: the gate verifies are_equivalent against this same `aut`.
    phi = try_heuristic_gate(aut)
    if phi is not None:
        return phi
    det = _to_split_form(aut)
    return _dispatch(det, reconstruct, decompose_kwargs, 0, max_depth)


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
