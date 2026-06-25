"""
portfolio/build.py — assemble a portfolio Translator from an Options + a cited
technique set.

Two modes, one entry point (`build_portfolio`):

* `techniques is None` — the shipped default: the `"default"` alias in
  `recipes.RECIPES` (currently → `best_daisy2`,
  `Simplify(strength(acceptance(daisy_pair(core))), "hi")` with
  `core = first(partscc, bls)` — the strength/acceptance decomposition over a
  daisy/daisy2 peel pair flooring on the bls cascade). The default is re-pointed by
  editing that one alias in `recipes/__init__.py`; `--use default` names it
  explicitly. (`--use best` is the prior daisy-only assembly.)

* `techniques` is a set/sequence of NAMES — the research path: cite the methods
  that may participate, everything else is knocked out, NO implicit floor. The
  cited PRODUCERS form a `first_success` ladder in CITED ORDER (cited order =
  priority):

      node = first_success([ <cited producers, in cited order> ])

  So `--use muller` is the general Muller-DNF leaf only; `--use buchi` runs ONLY
  the Büchi leaf and DECLINES on a non-Büchi language (no fallback); `--use
  buchi,muller` is a flat ladder tried in that order.

Producers. Six names are PRODUCERS (Translators that can be a ladder rung): the
five kr acceptance leaves `acc / weak / buchi / cobuchi / muller` (`muller` is the
general-case BLS fallback), and the integrated cascade `bls` (= `make_hierarchy_class`,
the full Theorem-2 dispatch chain — the whole bls engine as ONE producer, NOT a
first_success of separate leaves). A citation with no producer is an error —
nothing to produce. `--use bls` is the full kr cascade.

Cost note: the kr acceptance leaves all read the SAME holonomy cascade, so the
cited kr leaves are grouped into a single cascade-level `first_success` lifted
ONCE by `as_translator` (one GAP decomposition), positioned at the first cited kr
leaf.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from aut2ltl.combinators.first_success import first_success
from aut2ltl.contract import CascadeTranslator, Translator
from aut2ltl.options import Options
from aut2ltl.bls.aut2cas import as_translator
from aut2ltl.bls.definability import definability_gate
from aut2ltl.bls.hierarchy_class import make_hierarchy_class
from aut2ltl.bls.acc import acc as _acc
from aut2ltl.bls.buchi import buchi as _buchi
from aut2ltl.bls.cobuchi import cobuchi as _cobuchi
from aut2ltl.bls.weak import weak as _weak
from aut2ltl.bls.muller import muller as _muller
from .recipes import RECIPES

# The cited-technique vocabulary. KR leaves map to their CascadeTranslator member
# (lifted to a Translator via as_translator). `muller` is the general-case leaf
# (the BLS fallback); the name `bls` is reserved for the full cascade below.
_KR_MEMBERS: Dict[str, CascadeTranslator] = {
    "acc": _acc,
    "weak": _weak,
    "buchi": _buchi,
    "cobuchi": _cobuchi,
    "muller": _muller,
}
# Producers in canonical (architecture) order, used only for messages/help.
# `bls` is the integrated cascade (make_hierarchy_class) — the full engine, not a
# member of _KR_MEMBERS — it is lifted on its own in _from_techniques.
PRODUCERS: Tuple[str, ...] = ("acc", "weak", "buchi", "cobuchi", "muller", "bls")
TECHNIQUES: Tuple[str, ...] = PRODUCERS


def _from_techniques(options: Options, techniques: Iterable[str]) -> Translator:
    """Assemble the cited-technique ladder, in cited order."""
    techs: List[str] = list(techniques)
    unknown = [t for t in techs if t not in TECHNIQUES]
    if unknown:
        raise ValueError(
            f"unknown technique(s) {unknown}; choose from {list(TECHNIQUES)}"
        )

    kr_cited: List[str] = [t for t in techs if t in _KR_MEMBERS]

    # Build the producer ladder in cited order. The kr leaves collapse into one
    # cascade-level first_success (one decomposition), placed at the first cited
    # kr leaf.
    rungs: List[Translator] = []
    kr_rung_placed = False
    for t in techs:
        if t in _KR_MEMBERS:
            if not kr_rung_placed:
                members = [_KR_MEMBERS[name] for name in kr_cited]
                chain: CascadeTranslator = (
                    members[0] if len(members) == 1
                    else first_success(members, name="kr")
                )
                rungs.append(definability_gate(as_translator(chain)))
                kr_rung_placed = True
        elif t == "bls":
            # The integrated cascade (the full bls engine) as ONE producer (its own
            # lift, independent of any individually cited kr leaves), gated on
            # LTL-definability (the cascade is unsound on a non-LTL language).
            rungs.append(definability_gate(as_translator(make_hierarchy_class(options))))

    if not rungs:
        raise ValueError(
            "no producer technique cited; need at least one of "
            f"{list(PRODUCERS)} (got {techs})"
        )

    return rungs[0] if len(rungs) == 1 else first_success(rungs, name="cited")


def build_portfolio(
    options: Options, techniques: Optional[Iterable[str]] = None
) -> Translator:
    """Assemble a portfolio Translator. `techniques=None` ⇒ the shipped default,
    the `"default"` alias in `recipes.RECIPES` (re-point that one entry to change the
    default); a single recipe name from `recipes.RECIPES` (e.g. `best`, `best_inv`,
    or `default` itself) ⇒ that named assembly;
    otherwise a set/sequence of technique names ⇒ the cited ladder (cited order =
    priority, no implicit floor). Raises `ValueError` on an unknown name or a
    producer-free citation."""
    if techniques is None:
        return RECIPES["default"](options)
    techs = list(techniques)
    # A recipe name (e.g. `--use best`) resolves to a named assembly from recipes/.
    # Recipes are whole assemblies, not ladder rungs, so they are cited alone.
    if len(techs) == 1 and techs[0] in RECIPES:
        return RECIPES[techs[0]](options)
    return _from_techniques(options, techs)


__all__ = ["build_portfolio", "TECHNIQUES", "PRODUCERS"]
