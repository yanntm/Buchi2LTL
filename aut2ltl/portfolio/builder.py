"""
portfolio/builder.py — named assemblies ("recipes") over the translators.

A growing library of convenience builders. Each function takes an `Options` and
returns a ready `Translator` (`Language → LTLResult`), wiring the engines and the
(de)composition approaches into a useful whole and named for the shape it builds.
This is where the "good assemblies" found during exploration are written down so the
CLI (`--use <name>`) and the survey can run them and compare variants.

The building blocks (each a Translator or a Translator→Translator combinator):

    bls(options)     the bls cascade engine, lifted over the GAP holonomy
                     decomposition with the cached LTL-definability gate in front.
    daisy(child)     recursively peel self-loop daisies, flooring on `child`.
    best(options)    the shipped default: strength ∘ acceptance decomposition over a
                     daisy-peel whose core floor is `bls`.

`RECIPES` maps each public recipe name to its builder, so `build_portfolio` can
resolve `--use best` (and variants) to an assembly.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.first_success import first_success
from aut2ltl.recurse import recurse
from aut2ltl.bls.aut2cas import as_translator
from aut2ltl.bls.hierarchy_class import make_hierarchy_class
from aut2ltl.daisy import Daisy
from aut2ltl.daisy2 import Daisy2
from aut2ltl.partscc import PartScc
from aut2ltl.decomp.acceptance import AccDecompose
from aut2ltl.decomp.strength import StrengthDecompose
from aut2ltl.decomp.inv import Invariant
from aut2ltl.simplify_ltl import Simplify


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


def core(options: Optional[Options] = None) -> Translator:
    """The non-decomposed core floor: try `partscc` (label a single terminal SCC —
    exactly what a daisy peel hands an exit target), else fall to the `bls` cascade.
    `partscc` is cheap and tight where it fires (it retires the sl `t2` heuristic);
    `bls` is the always-answers floor."""
    return first_success([PartScc(), bls(options)], name="core")


def best(options: Optional[Options] = None) -> Translator:
    """The shipped default assembly: `strength(acceptance(daisy(core)))`.

    Splits the language by strength (∨ of weak/terminal/strong), then each part by
    acceptance conjunct (∧, on the deterministic form), and on each atom peels
    self-loop daisies before handing the residual core to `core` (partscc, else the
    bls cascade). The modern re-expression of the historical `Decompose / SlDriven /
    Decompose` graph, with `daisy` in place of the sl envelope and `partscc` for `t2`.

    One `hi` simplification sits OUTSIDE the whole assembly (our DAG combinators are
    size-indifferent, so a single final pass suffices — it replaces the per-Translator
    `_simp_f` the old `Sl`/`SlDriven` ran on their own output)."""
    return Simplify(StrengthDecompose(AccDecompose(daisy(core(options)))), "hi")


def best_daisy2(options: Optional[Options] = None) -> Translator:
    """The shipped `best` assembly with `daisy2` slipped into the peel layer:
    `strength ∘ acceptance` decomposition over the `daisy`/`daisy2` peel pair
    (`daisy_pair`) flooring on `core` (partscc, else the bls cascade). Identical to
    `best` except the peel tries the length-1 star `daisy2` before falling to the
    core — so a star SCC `daisy` cannot peel is taken by `daisy2` instead of
    descending straight to the cascade. The single `hi` simplification stays
    outside the whole assembly, exactly as in `best`."""
    return Simplify(
        StrengthDecompose(AccDecompose(daisy_pair(core(options)))), "hi")


def best_inv(options: Optional[Options] = None) -> Translator:
    """`best_daisy2` with the invariant layer in the loop: factor the global safety
    invariant `G(Σ)` out front (`Invariant`), then strength ∘ acceptance
    decomposition over the daisy/daisy2 peel pair flooring on `core`. The strip
    hands a simpler residual language to the rest of the assembly; sound for the one
    application (`L(A) = L(strip(A,Σ)) ∩ L(GΣ)`). A/B variant to see what the
    invariant layer buys on top of daisy2."""
    return Simplify(
        Invariant(StrengthDecompose(AccDecompose(daisy_pair(core(options))))), "hi")


# Public recipe names → builders. `build_portfolio` resolves `--use <name>` here.
RECIPES: Dict[str, Callable[[Optional[Options]], Translator]] = {
    "best": best,
    "best_daisy2": best_daisy2,
    "best_inv": best_inv,
}


__all__ = ["bls", "daisy", "daisy_pair", "core", "best", "best_daisy2",
           "best_inv", "RECIPES"]
