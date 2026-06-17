"""
Core backward LTL reconstruction logic (DAG-native).

`reconstruct_ltl` runs self-loop backward labeling over a TGBA and returns a
`Result` (`aut2ltl.result`): a hash-consed `spot.formula` DAG on success,
or `status=DECLINED` (`.formula` None) when no exact label exists. Every formula
is built as a `spot.formula` — an adopted `scc_labeler` formula
is spliced as a child node WITHOUT flattening (the kr-under-sl payoff: a
high-sharing core costs only its DAG, never its unfolded `str()`).

The shared automaton-side helpers live in `reconstruction_helpers.py`; this
module is just the engine + its recursive `label`.
"""

from typing import Callable, Optional, TYPE_CHECKING

import spot
import buddy

if TYPE_CHECKING:
    from aut2ltl.result import Result

# The two heuristics that can "rescue" certain multi-state SCCs before we
# give up and emit UNSUPPORTED.  Both are tried (and validated) early.
from .heuristics.size2_overapprox import try_size2_overapprox
from .heuristics.terminal_2scc import try_terminal_2scc_with_validation
from .reconstruction_helpers import (
    _compute_state_invariants,
    _apply_downstream_invariants,
    _inject_tn_fragments_and_compute_bad_states,
    _sub_automaton_from,
    _compute_technique,
)

F = spot.formula
UNSUPPORTED = "UNSUPPORTED: non-trivial cycle or complex SCC"


def _is_unsupported(val):
    """True if val is the UNSUPPORTED string sentinel. Formula objects (the
    success path) are not str, so they pass through as not-unsupported."""
    return isinstance(val, str) and "UNSUPPORTED" in val


def reconstruct_ltl(
    aut: "spot.twa_graph",
    scc_labeler: Optional[Callable[["spot.twa_graph"], Optional["spot.formula"]]] = None,
) -> "Result":
    """Backward LTL reconstruction from a TGBA. Returns a `Result`
    (`aut2ltl.result`): on success `.formula` is a spot.formula and `.status`
    is OK; on decline `.status` is DECLINED and `.formula` is None. `.technique`
    is the method-token set (e.g. {"sl","t2"}). Uniform with the kr portfolio
    result.

    `scc_labeler` (optional, default None): a callback `sub_automaton ->
    spot.formula_or_None`. When sl reaches a state q it cannot translate
    exactly (a multi-state SCC -> normally UNSUPPORTED), it instead delegates
    the whole sub-automaton from q (`_sub_automaton_from`) to this callback; a
    returned formula is spliced in as label(q) (NO flattening) and the normal
    backward labeling continues around it (X-wrapped at the crossing edge, like
    any successor). This is the "kr under sl" seam: sl handles the very-weak
    envelope exactly, the callback (kr) handles the multi-cyclic core — on a
    SMALLER automaton than the whole. Sound when the callback is sound (the
    delegated label plays the exact role of sl's own label(q))."""

    # --- Heuristic layer: try to absorb size-2 non-accepting SCCs (f2) ---
    massaged = try_size2_overapprox(aut)
    absorbed = False
    if massaged is not None:
        aut = massaged
        absorbed = True   # trust the heuristic; skip the strict multi-state filter

    # --- Precompute downstream invariants per state (once, up front) ---
    # As FORMULAS (None when empty).
    state_invariant_literals = _compute_state_invariants(aut)
    state_invariants = {}
    for q, lits in state_invariant_literals.items():
        if lits:
            lit_fs = [F.Not(F.ap(l[1:])) if l.startswith("!") else F.ap(l)
                      for l in sorted(lits)]
            state_invariants[q] = F.G(F.And(lit_fs))
        else:
            state_invariants[q] = None

    # Simplify outgoing edge labels by existentially quantifying downstream
    # invariants. This is sound ONLY because the linear walk re-adds each
    # invariant (timed, X-wrapped) as it ENTERS the owning state. Full-suffix
    # delegation skips that walk, so it must NOT see the stripped automaton: a
    # stripped INTERIOR invariant (e.g. a terminal sink's `G a`) would never be
    # re-added and the delegate would translate a widened language (an unsound
    # over-approximation — the `a`-for-(a!a)*a^w bug). We keep the pre-strip
    # automaton and root delegation on it (numbering is preserved, so q indexes
    # both identically).
    pristine_aut = aut
    aut = _apply_downstream_invariants(aut, state_invariant_literals)

    # --- Terminal-SCC (t2/tN) labeling heuristic: pre-validated G(...) fragments ---
    nice_terminal_sccs = try_terminal_2scc_with_validation(aut)
    scc_fragments = {}   # state -> validated formula fragment for its SCC
    scc_entry_I = {}     # state -> BDD of I(s): entry letters must imply it
    for info in nice_terminal_sccs:
        validated = info.get("validated_formula") or info.get("simplified")
        if validated:
            for st in info["states"]:
                # t2 emits a spot.formula DAG (see terminal_2scc); use directly.
                scc_fragments[st] = validated
                if "L_bdd" in info and st in info["L_bdd"]:
                    scc_entry_I[st] = info["L_bdd"][st]

    # --- Trivial acceptance normalization ---
    treat_all_as_accepting = (aut.acc().num_sets() == 0)

    state_formula = {}
    visiting = set()
    bad_states, state_formula = _inject_tn_fragments_and_compute_bad_states(
        aut, scc_fragments, state_formula, absorbed
    )

    # States in a multi-state SCC (>=2 states) are sl's hard cases — bottom OR
    # transient. With an scc_labeler set we delegate the whole sub-automaton from
    # such a state (full-suffix delegation) at label() entry.
    _multi_scc_states = set()
    if scc_labeler is not None:
        _si = spot.scc_info(aut)
        for _s in range(_si.scc_count()):
            _members = _si.states_of(_s)
            if len(_members) >= 2:
                _multi_scc_states.update(int(x) for x in _members)

    MAX_DEPTH = 10000
    depth = [0]
    d = aut.get_dict()

    def label(q):
        if q in state_formula:
            return state_formula[q]

        # Full-suffix delegation (kr under sl): a formula from the callback is
        # spliced WITHOUT flattening (the DAG payoff). Entry placement pre-empts
        # both the bad_states and the `visiting` decline paths.
        if scc_labeler is not None and q in _multi_scc_states:
            try:
                # Pre-strip automaton: the delegate must see the invariant intact
                # (see _apply_downstream_invariants note above).
                frag = scc_labeler(_sub_automaton_from(pristine_aut, q))
            except Exception:
                frag = None
            if frag is not None:
                state_formula[q] = frag
                return frag

        if q in bad_states:
            state_formula[q] = UNSUPPORTED
            return UNSUPPORTED

        # t2 short-circuit: a validated G(...) fragment for exactly this state.
        # Emit it and do NOT walk the SCC's self-loops / exits.
        if q in scc_fragments:
            phi = scc_fragments[q]
            state_formula[q] = phi
            return phi

        if q in visiting:
            state_formula[q] = UNSUPPORTED
            return UNSUPPORTED

        if depth[0] > MAX_DEPTH:
            state_formula[q] = UNSUPPORTED
            return UNSUPPORTED

        visiting.add(q)
        depth[0] += 1

        current_inv = state_invariants.get(q)

        self_loops = []   # list of (cond_formula, acc_sets)
        exit_terms = []   # list of formulas

        for e in aut.out(q):
            cond = spot.bdd_to_formula(e.cond, d)

            if treat_all_as_accepting:
                acc_sets = frozenset()
            else:
                acc_sets = frozenset(e.acc.sets())

            if e.src == e.dst:
                self_loops.append((cond, acc_sets))
                continue

            # Strict hardening: a successor inside a multi-state SCC with no
            # fragment -> the whole state is UNSUPPORTED. (With an scc_labeler we
            # fall through so label(e.dst) can delegate the sub-automaton.)
            if (e.dst in bad_states and e.dst not in state_formula
                    and e.dst not in scc_fragments and scc_labeler is None):
                state_formula[q] = UNSUPPORTED
                visiting.discard(q)
                depth[0] -= 1
                return UNSUPPORTED

            # Per-transition entry timing into a t2 SCC fragment: if the crossing
            # letter implies the target's I(s), attach synchronously; else delayed.
            direct_scc_sync_attach = False
            if e.dst in scc_fragments:
                succ_phi = scc_fragments[e.dst]
                i_bdd = scc_entry_I.get(e.dst)
                if i_bdd is not None:
                    if (e.cond & buddy.bdd_not(i_bdd)) == buddy.bddfalse:
                        direct_scc_sync_attach = True
            else:
                succ_phi = label(e.dst)
                if _is_unsupported(succ_phi):
                    # Never wrap the sentinel into a compound term.
                    state_formula[q] = UNSUPPORTED
                    visiting.discard(q)
                    depth[0] -= 1
                    return UNSUPPORTED

            # --- Connection rule: successor label AND its downstream invariant ---
            inv_formula = state_invariants.get(e.dst)

            if e.dst in scc_fragments:
                # SCC case: always X the invariant part (it already contains its G);
                # sync vs X for the fragment itself via direct_scc_sync_attach.
                scc_wrapped = succ_phi if direct_scc_sync_attach else F.X(succ_phi)
                term = F.And([scc_wrapped, F.X(inv_formula)]) if inv_formula is not None else scc_wrapped
            else:
                # Normal successor: label AND invariant (same timing).
                term = F.And([succ_phi, inv_formula]) if inv_formula is not None else succ_phi

            cond_true = cond.is_tt()
            if current_inv is not None:
                edge_prefix = current_inv if cond_true else F.And([cond, current_inv])
                if e.dst in scc_fragments:
                    exit_terms.append(F.And([edge_prefix, term]))
                else:
                    exit_terms.append(F.And([edge_prefix, F.X(term)]))
            else:
                if e.dst in scc_fragments:
                    exit_terms.append(term if cond_true else F.And([cond, term]))
                else:
                    exit_terms.append(F.X(term) if cond_true else F.And([cond, F.X(term)]))

        # Pre-construction safety: a sentinel among the pieces aborts cleanly.
        if any(_is_unsupported(c) for c, _ in self_loops) or any(_is_unsupported(p) for p in exit_terms):
            state_formula[q] = UNSUPPORTED
            visiting.discard(q)
            depth[0] -= 1
            return UNSUPPORTED

        # Apply reconstruction rules
        if not exit_terms and self_loops:
            or_all = F.Or([c for c, _ in self_loops])

            touched_sets = set()
            for _, acc in self_loops:
                touched_sets.update(acc)
            local_num_sets = len(touched_sets)

            if local_num_sets <= 1 or treat_all_as_accepting:
                acc_cs = [c for c, acc in self_loops if acc]
                if acc_cs:
                    phi = F.And([F.G(or_all), F.G(F.F(F.Or(acc_cs)))])
                else:
                    phi = F.G(or_all)
            else:
                # Generalized Büchi: G(OR all) & GF(cover_i) per touched acc set.
                gfs = []
                for i in sorted(touched_sets):
                    covering = [c for c, acc in self_loops if i in acc]
                    if covering:
                        gfs.append(F.G(F.F(F.Or(covering))))
                phi = F.And([F.G(or_all)] + gfs) if gfs else F.G(or_all)

            if current_inv is not None:
                phi = F.And([phi, current_inv])

        elif exit_terms:
            or_ex = F.Or(exit_terms)
            has_acc = any(acc for _, acc in self_loops) or (treat_all_as_accepting and bool(self_loops))

            if has_acc:
                # "stay forever" must cover each required Inf set i.o.; plus the
                # "leave" option (or_self U exit).
                touched_sets = set()
                for _, acc in self_loops:
                    touched_sets.update(acc)
                local_num_sets = len(touched_sets)

                or_self = F.Or([c for c, _ in self_loops])

                if local_num_sets <= 1 or treat_all_as_accepting:
                    acc_cs = [c for c, acc in self_loops if acc]
                    or_acc = F.Or(acc_cs) if acc_cs else F.tt()
                    stay = F.And([F.G(or_self), F.G(F.F(or_acc))])
                else:
                    gfs = []
                    for i in sorted(touched_sets):
                        covering = [c for c, acc in self_loops if i in acc]
                        if covering:
                            gfs.append(F.G(F.F(F.Or(covering))))
                    stay = F.And([F.G(or_self)] + gfs) if gfs else F.G(or_self)

                if current_inv is not None:
                    stay = F.And([stay, current_inv])
                or_self_u = F.And([or_self, current_inv]) if current_inv is not None else or_self
                phi = F.Or([stay, F.U(or_self_u, or_ex)])
            else:
                if self_loops:
                    or_self = F.Or([c for c, _ in self_loops])
                    if current_inv is not None:
                        or_self = F.And([or_self, current_inv])
                    phi = F.U(or_self, or_ex)
                else:
                    phi = or_ex
        else:
            phi = F.ff()

        state_formula[q] = phi
        visiting.discard(q)
        depth[0] -= 1
        return phi

    init = aut.get_init_state_number()
    final = label(init)
    technique = _compute_technique(absorbed, nice_terminal_sccs)
    # Lazy import: buchi2ltl is the separate engine; the shared result struct
    # lives in kr/ for now (the resulting import cycle is deferred to a later
    # `util` extraction — agreed 2026-06-14). No load-time cycle: `import kr`
    # does not import buchi2ltl (the gate's buchi2ltl import is lazy).
    from aut2ltl.result import Result
    techset = set(technique.split("+")) if technique else set()
    if _is_unsupported(final):
        # Contract boundary: the internal UNSUPPORTED sentinel becomes an
        # explicit DECLINED status (no sentinel string in `.formula`).
        return Result.decline(None, *techset)
    return Result.success(final, *techset)
