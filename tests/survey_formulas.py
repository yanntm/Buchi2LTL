#!/usr/bin/env python3
"""
tests/survey_formulas.py — the curated survey corpus, in isolation.

This is the ONE place the survey formulas live. They used to be nested inline in
each survey script (`survey_mp_cascade.py`, `survey_sizes.py`); pulling them out
lets `tests/survey.py` (and any future HOA-input survey) share a single,
documented corpus, and lets the corpus be reviewed/extended without touching the
runner.

Each entry is a `SurveyCase(formula, klass, note)`:
  * `formula` — an LTL string in Spot syntax (mind the spaces: "q U r" is the
    until of q and r; "qUr" is a single atomic proposition).
  * `klass`   — the Manna-Pnueli class we expect (B bottom, S safety,
    G guarantee, O obligation, R recurrence, P persistence, T reactivity);
    a label for grouping, NOT asserted — the survey also reads spot.mp_class.
  * `note`    — WHY this formula is in the corpus (what it exercises / why it was
    historically interesting).

The corpus spans the MP hierarchy weakest-first and folds in the cases that were
hard during construction (the former equiv residuals recorded in
aut2ltl/bls/STATUS.md), so a regression on any of them shows up immediately.
"""
from __future__ import annotations

from typing import List, NamedTuple


class SurveyCase(NamedTuple):
    """One corpus formula with its expected MP class and a rationale."""

    formula: str
    klass: str
    note: str


# Weakest-first across the Manna-Pnueli hierarchy. Kept small (1-2 APs, small
# automata) so cascades stay tractable and any failure is debuggable.
SURVEY_CASES: List[SurveyCase] = [
    # -- bottom / trivial -------------------------------------------------
    SurveyCase("true", "B", "degenerate: empty cascade, must round-trip to true"),
    SurveyCase("false", "B", "degenerate: empty language, must round-trip to false"),
    SurveyCase("a", "G", "single-letter guarantee; smallest non-trivial case"),

    # -- safety (G-rooted invariants) -------------------------------------
    SurveyCase("Ga", "S", "pure invariant; smallest safety"),
    SurveyCase("G(a | b)", "S", "invariant over a boolean guard"),
    SurveyCase("G(a -> X b)", "S", "invariant with a next-step obligation (2-step safety)"),
    SurveyCase("a & X a", "S", "bounded safety; no fixpoint, finite horizon"),
    SurveyCase("G(a -> X a)", "S", "stutter/latch invariant; a former equiv residual"),
    SurveyCase("G(a & X a)", "S", "invariant whose body already spans two steps"),

    # -- depth ladder: each X adds one cascade level ----------------------
    # (Xa=3L, XXa=4L, XXXa=5L) — simplest probes of DEEP cascades.
    SurveyCase("X a", "G", "depth ladder: 3-level cascade"),
    SurveyCase("X X a", "G", "depth ladder: 4-level cascade"),
    SurveyCase("X X X a", "G", "depth ladder: 5-level cascade"),
    SurveyCase("X(a & X a)", "G", "depth ladder: branching next, 5-level"),

    # -- guarantee (co-safety, F-reachable) -------------------------------
    SurveyCase("Fa", "G", "pure reachability; smallest liveness"),
    SurveyCase("a U b", "G", "until: the canonical guarantee with a hold condition"),
    SurveyCase("F(a & b)", "G", "reach a boolean state"),
    SurveyCase("F(a & X b)", "G", "reach-then-next; a former equiv residual (reach-driven)"),
    SurveyCase("a | X b", "G", "boolean over a next; shallow co-safety"),

    # -- obligation (boolean combinations of safety + guarantee) ----------
    SurveyCase("Fa | Gb", "O", "obligation: reachability OR invariant"),
    SurveyCase("Ga | Gb", "O", "disjunction of invariants"),
    SurveyCase("Fa & Gb", "O", "reach while maintaining an invariant"),
    SurveyCase("(a U b) | Gc", "O", "until OR invariant"),
    SurveyCase("Ga | Fb", "O", "the mixed safety/guarantee obligation"),

    # -- recurrence (Buchi / Pi_2: infinitely-often) ----------------------
    SurveyCase("GFa", "R", "smallest recurrence; the Buchi acceptance core"),
    SurveyCase("G(a -> F b)", "R", "request/response; a former equiv residual"),
    SurveyCase("G(a | F b)", "R", "response variant; a former equiv residual"),
    SurveyCase("GFa & GFb", "R", "conjunctive recurrence; AND-splits per acceptance set"),
    SurveyCase("GFa & GFb & GFc", "R", "three-way conjunctive recurrence; a former wall"),
    SurveyCase("G(a -> F b) & G(c -> F d)", "R", "two independent response conjuncts"),
    SurveyCase("G(p -> (q U r))", "R",
               "the challenge case: reach-driven, none(1); track every run"),

    # -- persistence (coBuchi / Sigma_2: eventually-always) ---------------
    SurveyCase("FGa", "P", "smallest persistence; the coBuchi core"),
    SurveyCase("F(a & G b)", "P", "reach then hold forever"),
    SurveyCase("FGa | FGb", "P", "disjunctive persistence; the last equiv wall"),

    # -- reactivity (full Rabin/Streett, Pi_2 & Sigma_2 mix) --------------
    SurveyCase("GFa -> GFb", "T", "the canonical reactivity (one Rabin pair)"),
    SurveyCase("GFa & FGb", "T", "Inf & Fin Rabin-pair conjunct; AND-splits"),

    # -- partscc stress: deterministic terminal-SCC partition (aut2ltl.partscc)
    # Languages whose terminal SCC is letter-deterministic (disjoint L-labels),
    # which the partscc leaf reconstructs to one anchored G(...) (+ GF per color).
    # Span: phase-dependent (alternating) safety, then deterministic generalized
    # Buchi with one and two acceptance colors.
    SurveyCase("G((!a & X a) | (a & X !a))", "S",
               "partscc: alternating terminal SCC; phase-dependent entry (anchor)"),
    SurveyCase("G(a <-> X b)", "S",
               "partscc: 2-step coupled invariant; phase-dependent terminal SCC"),
    SurveyCase("GFa & G(a -> X !a)", "R",
               "partscc: deterministic Buchi SCC (a i.o., no two a's running)"),
    SurveyCase("G(a -> X b) & GFa", "R",
               "partscc: deterministic SCC carrying one fairness color"),
    SurveyCase("GFa & GFb & G(a -> X !a)", "R",
               "partscc: deterministic generalized-Buchi SCC, two colors"),
]

# Plain formula list (the runner's default when no arg is given).
SURVEY_FORMULAS: List[str] = [c.formula for c in SURVEY_CASES]

# Lookup: formula -> expected MP-class label (for CSV/report annotation).
KLASS_OF: dict = {c.formula: c.klass for c in SURVEY_CASES}

__all__ = ["SurveyCase", "SURVEY_CASES", "SURVEY_FORMULAS", "KLASS_OF"]
