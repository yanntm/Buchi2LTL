"""
portfolio/builder.py — the building BLOCKS the recipes assemble.

A small library of reusable builders: each is a `Translator` (`Language →
LTLResult`) or a `Translator → Translator` combinator, wiring the engines and the
(de)composition approaches into a peel/floor shape named for what it builds. The
*recipes* that compose these blocks into named, `--use`-resolvable assemblies live
one-per-module under `portfolio/recipes/` (which exposes the `RECIPES` registry);
the blocks stay here so several recipes can share them.

The blocks:

    bls(options)          the bls cascade engine, lifted over the GAP holonomy
                          decomposition with the cached LTL-definability gate in front.
    core(options)         the non-decomposed floor: `first(partscc, bls)`.
    daisy(child)          recursively peel self-loop daisies, flooring on `child`.
    daisy_pair(child)     `daisy` with the length-1 star `daisy2` slipped in.
    daisy_pair_inv(child) `daisy_pair` with the invariant strip woven per descent.
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.first_success import first_success
from aut2ltl.recurse import recurse
from aut2ltl.bls.aut2cas import as_translator
from aut2ltl.bls.hierarchy_class import make_hierarchy_class
from aut2ltl.daisy import Daisy
from aut2ltl.daisy2 import Daisy2
from aut2ltl.daisystar import Daisystar
from aut2ltl.daisystardet import DaisystarDet
from aut2ltl.partscc import PartScc
from aut2ltl.decomp.inv import Invariant


def bls(options: Optional[Options] = None) -> Translator:
    """The bls cascade engine as a Translator. Lifts the acceptance-dispatch ladder
    (acc → weak → buchi → cobuchi → muller) over the Krohn-Rhodes holonomy
    decomposition (`as_translator`), which runs the cached LTL-definability gate
    first. The general-case floor: it always answers — a formula, or a NOT_LTL
    verdict when the language is not LTL-definable."""
    return as_translator(make_hierarchy_class(options))


def daisy(child: Translator) -> Translator:
    """Recursively peel self-loop daisies, delegating residual cores to `child`.

    `recurse` ties the knot, `first_success` is the per-level choice: try `Daisy`,
    else fall to `child`. The `Daisy` peel hands each exit target back to `leaf`
    (THIS assembly), so a chain of nested daisies peels one center at a time; when
    the head is not a daisy the peel declines and `child` (e.g. `bls`) takes the
    whole. Every stem strictly descends, so the recursion is well-founded; `child`
    must not re-enter `daisy` on a single multi-state SCC (bls is a flat floor)."""
    return recurse(lambda leaf: first_success([Daisy(leaf), child], name="daisy"))


def daisy_pair(child: Translator) -> Translator:
    """Like `daisy(child)` but with the length-1 star `daisy2` slipped in between
    the self-loop `daisy` and the floor: per level try `Daisy`, then `Daisy2`
    (gated by a Spot oracle), then `child`; each peel hands its stem exits back to
    `leaf`. Same well-founded recursion as `daisy` — every stem strictly descends,
    and `daisy2` resolves a whole star SCC without recursing into it, so `child`
    is still a flat floor (`core`, or a declining unit)."""
    return recurse(
        lambda leaf: first_success([Daisy(leaf), Daisy2(leaf), child],
                                   name="daisy_pair"))


def daisy_trio(child: Translator) -> Translator:
    """Like `daisy_pair` but with the rejecting length-1 star `daisystar` added to
    the peel: per level try `Daisy`, then `Daisy2` (the recurrence star, gated),
    then `Daisystar` (the reachability star — a rejecting star that exits to a
    sink, gated), then `child`. Each peel hands its stem exits back to `leaf`;
    same well-founded recursion as `daisy` (every stem strictly descends, and
    `daisystar` resolves a whole star SCC without recursing into it)."""
    return recurse(
        lambda leaf: first_success(
            [Daisy(leaf), Daisy2(leaf), Daisystar(leaf), child], name="daisy_trio"))


def daisy_trio_inv(child: Translator) -> Translator:
    """`daisy_trio` with the invariant strip woven into EVERY descent level, exactly
    as `daisy_pair_inv` does for `daisy_pair`: each recursion factors its
    sub-automaton's local `G(Σ)`, peels (`Daisy` → `Daisy2` → `Daisystar` → child),
    and re-asserts `G(Σ)`."""
    return recurse(
        lambda leaf: Invariant(
            first_success([Daisy(leaf), Daisy2(leaf), Daisystar(leaf), child],
                          name="daisy_trio")))


def daisy_trio_det(child: Translator) -> Translator:
    """`daisy_trio` with the deterministic read-off `DaisystarDet` slipped in ahead
    of the flat `Daisystar`: per level try `Daisy`, `Daisy2`, then `DaisystarDet`
    (the exact, fixpoint-free anchored form for a rejecting SCC with a
    deterministic L-partition), then `Daisystar` (the flat fallback for a
    *non*-deterministic rejecting star), then `child`. Coverage is therefore at
    least `daisy_trio`'s; a deterministic rejecting star gets the smaller exact
    form instead of the gated flat one."""
    return recurse(
        lambda leaf: first_success(
            [Daisy(leaf), Daisy2(leaf), DaisystarDet(leaf), Daisystar(leaf), child],
            name="daisy_trio_det"))


def daisy_trio_det_inv(child: Translator) -> Translator:
    """`daisy_trio_det` with the invariant strip woven into every descent level
    (cf. `daisy_trio_inv` / `daisy_pair_inv`)."""
    return recurse(
        lambda leaf: Invariant(
            first_success(
                [Daisy(leaf), Daisy2(leaf), DaisystarDet(leaf), Daisystar(leaf), child],
                name="daisy_trio_det")))


def daisy_pair_inv(child: Translator) -> Translator:
    """`daisy_pair` with the invariant strip woven into EVERY descent level: each
    recursion first factors its sub-automaton's *local* `G(Σ)` (`Invariant`), peels
    the stripped residual, and re-asserts `G(Σ)`. The `recurse` step wraps the
    per-level peel in `Invariant`, so as the peel descends each stem target is
    inv-stripped on the way in — unlike top-only `best_inv`, where the *global*
    `Σ = ⋁(all guards)` is usually vacuous. Sound per level (each `Invariant` is one
    self-contained strip + re-assert around one peel call)."""
    return recurse(
        lambda leaf: Invariant(
            first_success([Daisy(leaf), Daisy2(leaf), child], name="daisy_pair")))


def core(options: Optional[Options] = None) -> Translator:
    """The non-decomposed core floor: try `partscc` (label a single terminal SCC —
    exactly what a daisy peel hands an exit target), else fall to the `bls` cascade.
    `partscc` is cheap and tight where it fires (it retires the sl `t2` heuristic);
    `bls` is the always-answers floor."""
    return first_success([PartScc(), bls(options)], name="core")


__all__ = ["bls", "daisy", "daisy_pair", "daisy_pair_inv",
           "daisy_trio", "daisy_trio_inv",
           "daisy_trio_det", "daisy_trio_det_inv", "core"]
