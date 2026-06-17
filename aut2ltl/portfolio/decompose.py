"""
portfolio/decompose.py — the `Decompose` Translator (Composite + Decorator).

`Decompose(leaf: Translator)` IS a Translator: given a `Language` it splits the
language (AND by acceptance conjunct / OR by strength) and recombines the parts
with a root boolean operator, recursing on ITSELF so nested splits fall out; when
the language does not split it delegates the whole to `leaf`. No special cases —
each Translator pulls the representation it wants from the `Language` it is
handed; `Decompose` only splits (on the determinized form), recombines, and
delegates.

Soundness (kr/sl are language-faithful; a ROOT boolean op is a pure position-0
language op — no temporal-placement / acceptance-coupling caveats):

  * AND by acceptance set.  On a DETERMINISTIC automaton every word has one run,
    so for conjunctive acceptance  acc = ⋀ᵢ cᵢ:
        L(A) = ⋂ᵢ L(A | acc:=cᵢ)        (shared run -> exact)
    Determinism is REQUIRED here (on a nondeterministic automaton ⋂L(Aᵢ) ⊋ L(A)).

  * OR by strength.  Spot's strength decomposition splits an automaton into
    weak / terminal / strong sub-automata whose UNION is the language
    (Renault et al., TACAS'13; exact for any automaton):
        L(A) = ⋃ₖ L(decompose_scc(A,k))

The split form is `Language.det_generic_minimal()` — deterministic (the AND-split
precondition), generic (keeps the generalized-Büchi ⋀Inf / Streett conjunctive
shape instead of collapsing to parity), state-minimal (kr's census is acutely
state-count sensitive). `recombine` declines if any part declines — the split is
sound only if every part reconstructs.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import spot

from aut2ltl.contract import Translator
from aut2ltl.result import Result, fuse
from aut2ltl.language import Language
from aut2ltl.ltl.builders import own_simplify


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


def _split(aut: "spot.twa_graph") -> Tuple[Optional[str], List["spot.twa_graph"]]:
    """How the root splits this (deterministic) automaton: ('and'|'or', pieces),
    or (None, []) when it is atomic. Conjunctive first, else multi-strength."""
    and_p = _and_pieces(aut)
    if and_p:
        return ("and", and_p)
    or_p = _or_pieces(aut)
    if or_p:
        return ("or", or_p)
    return (None, [])


def _recombine(op: str, subs: List[Result]) -> Result:
    """Recombine sub-results with the root ⋀/⋁ via the accumulator idiom: seed an
    OK result with {op<n>}, `fuse` every part in (worst status wins, all diagnoses
    accumulated), and bail if the fold is NOK — a NOT_LTL part is propagated as the
    verdict, a declined part as a decline, each carrying every part's reason. On OK,
    fill in the And/Or of the part formulas; technique = ⋃ parts ∪ {op<n>}."""
    res = fuse(Result.start(f"{op}{len(subs)}"), *subs)   # credit each part; accumulate reasons
    if res.nok:
        return res
    # Run the own-rules simplifier (NOT Spot's — it is not DAG-size aware)
    # on the parts BEFORE combining and on the combo AFTER: the recombined
    # And/Or is a node no per-node pass ever saw whole, so cross-part folds
    # (e.g. `G(!b&h) | (h U b)` → `h W b`) only fire here.
    forms = [own_simplify(s.formula) for s in subs]
    f = spot.formula.And(forms) if op == "and" else spot.formula.Or(forms)
    res.formula = own_simplify(f)
    return res


class Decompose:
    """The decompose-and-recombine Composite as a Translator over a leaf
    Translator. Splits unconditionally when it can (recursing on itself), else
    delegates the whole `Language` to `leaf`. Transparent on technique: it adds
    `and<n>`/`or<n>` and forwards the parts' techniques."""

    name = "decompose"

    def __init__(self, leaf: Translator) -> None:
        self._leaf = leaf

    def __call__(self, lang: Language) -> Result:
        op, pieces = _split(lang.det_generic_minimal())
        if pieces:
            return _recombine(op, [self(Language.of(p)) for p in pieces])
        return self._leaf(lang)


def split_report(lang: Language) -> Tuple[str, int]:
    """Diagnose how the root would split this language (no reconstruction).
    Returns (kind, n_pieces): kind in {'and','or','none'}."""
    op, pieces = _split(lang.det_generic_minimal())
    return (op, len(pieces)) if op else ("none", 1)


__all__ = ["Decompose", "split_report", "_split"]
