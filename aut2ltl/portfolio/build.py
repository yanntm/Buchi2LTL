"""
portfolio/build.py — assemble a portfolio Translator from an Options + a cited
technique set.

Two modes, one entry point (`build_portfolio`):

* `techniques is None` — the shipped default: the `best` recipe
  (`builder.RECIPES["best"]`), `Simplify(strength(acceptance(daisy(core))), "hi")`
  with `core = first(partscc, bls)`. The modern, sl-free re-expression of the
  historical `Decompose / SlDriven / Decompose` graph (`daisy` in place of the sl
  envelope, `partscc` in place of `t2`) — smaller and sounder (see HISTORY
  2026-06-18).

* `techniques` is a set/sequence of NAMES — the research path: cite the methods
  that may participate, everything else is knocked out, NO implicit floor. The
  cited PRODUCERS form a `first_success` ladder in CITED ORDER (cited order =
  priority); the two WRAPPERS wrap that ladder when present:

      node = first_success([ <cited producers, in cited order> ])
      if 'sl_driven' cited:  node = SlDriven(node)      # inner
      if 'decompose' cited:  node = Decompose(node)     # outer

  So `--use bls` is pure BLS-from-Muller; `--use buchi` runs ONLY the Büchi leaf
  and DECLINES on a non-Büchi language (no fallback); `--use sl,buchi,bls` is a
  flat ladder tried in that order; `--use decompose,acc,bls` wraps the ladder.

Producers vs wrappers. Seven names are PRODUCERS (Translators that can be a
ladder rung): the five kr acceptance leaves `acc / weak / buchi / cobuchi / bls`,
the integrated default cascade `str` (= `make_hierarchy_class`, the full
Theorem-2 dispatch chain INCLUDING acc — the kr core as ONE producer, the same
object the default portfolio calls `cascade`, NOT a first_success of separate
leaves), and the heuristic `sl` gate. Two are WRAPPERS (they take a leaf/delegate,
so they wrap the ladder rather than sit in it): `sl_driven` and `decompose`. A
citation with no producer (e.g. `--use decompose` alone) is an error — nothing to
produce. `--use str` is the bare kr cascade; `--use decompose,str` is the kr core
under the AND/OR strength decomposition (the default minus the sl gate).

Cost note: the kr acceptance leaves all read the SAME holonomy cascade, so the
cited kr leaves are grouped into a single cascade-level `first_success` lifted
ONCE by `as_translator` (one GAP decomposition), positioned at the first cited kr
leaf. The `sl` gate keeps its own cited position. The only consequence is that an
`sl` cited strictly BETWEEN two kr leaves is ordered relative to the kr group as a
whole, not interleaved into it — an unusual citation, and the architecture tries
the cheap sl gate before the cascade anyway.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from aut2ltl.first_success import first_success
from aut2ltl.contract import CascadeTranslator, Translator
from aut2ltl.options import Options
from aut2ltl.bls.aut2cas import as_translator
from aut2ltl.bls.hierarchy_class import make_hierarchy_class
from aut2ltl.bls.acc import acc as _acc
from aut2ltl.bls.buchi import buchi as _buchi
from aut2ltl.bls.cobuchi import cobuchi as _cobuchi
from aut2ltl.bls.weak import weak as _weak
from aut2ltl.bls.bls import bls as _bls
from .sl import Sl
from .sl_driven import SlDriven
from .decompose import Decompose
from .builder import RECIPES

# The cited-technique vocabulary. KR leaves map to their CascadeTranslator member
# (lifted to a Translator via as_translator); `sl` is already a Translator. The
# two wrappers carry no member — they decorate the assembled ladder.
_KR_MEMBERS: Dict[str, CascadeTranslator] = {
    "acc": _acc,
    "weak": _weak,
    "buchi": _buchi,
    "cobuchi": _cobuchi,
    "bls": _bls,
}
# Producers in canonical (architecture) order, used only for messages/help.
# `str` is the integrated cascade (make_hierarchy_class), not a member of
# _KR_MEMBERS — it is lifted on its own in _from_techniques.
PRODUCERS: Tuple[str, ...] = ("acc", "weak", "buchi", "cobuchi", "bls", "str", "sl")
WRAPPERS: Tuple[str, ...] = ("sl_driven", "decompose")
TECHNIQUES: Tuple[str, ...] = PRODUCERS + WRAPPERS


def _default_portfolio(options: Options) -> Translator:
    """The hand-tuned best default (the historical `reconstruct_decomposed`)."""
    sl = Sl(options)
    cascade = as_translator(make_hierarchy_class(options))
    core = Decompose(first_success([sl, cascade], name="core"))
    sl_driven = SlDriven(delegate=core)
    return Decompose(first_success([sl_driven, cascade], name="top"))


def _from_techniques(options: Options, techniques: Iterable[str]) -> Translator:
    """Assemble the cited-technique ladder (+ wrappers), in cited order."""
    techs: List[str] = list(techniques)
    unknown = [t for t in techs if t not in TECHNIQUES]
    if unknown:
        raise ValueError(
            f"unknown technique(s) {unknown}; choose from {list(TECHNIQUES)}"
        )

    kr_cited: List[str] = [t for t in techs if t in _KR_MEMBERS]

    # Build the producer ladder in cited order. The kr leaves collapse into one
    # cascade-level first_success (one decomposition), placed at the first cited
    # kr leaf; the sl gate sits at its own cited position.
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
                rungs.append(as_translator(chain))
                kr_rung_placed = True
        elif t == "str":
            # The integrated default cascade as ONE producer (its own lift,
            # independent of any individually cited kr leaves).
            rungs.append(as_translator(make_hierarchy_class(options)))
        elif t == "sl":
            rungs.append(Sl(options))
        # 'sl_driven' / 'decompose' are wrappers, applied below.

    if not rungs:
        raise ValueError(
            "no producer technique cited; need at least one of "
            f"{list(PRODUCERS)} (got only wrappers {techs})"
        )

    node: Translator = rungs[0] if len(rungs) == 1 else first_success(
        rungs, name="cited"
    )
    if "sl_driven" in techs:
        node = SlDriven(delegate=node)
    if "decompose" in techs:
        node = Decompose(node)
    return node


def build_portfolio(
    options: Options, techniques: Optional[Iterable[str]] = None
) -> Translator:
    """Assemble a portfolio Translator. `techniques=None` ⇒ the shipped default,
    the `best` recipe (`builder.RECIPES["best"]`); a single recipe name from
    `builder.RECIPES` (e.g. `best`) ⇒ that named assembly; otherwise a set/sequence
    of technique names ⇒ the cited ladder (cited order = priority, no implicit
    floor). Raises `ValueError` on an unknown name or a producer-free citation."""
    if techniques is None:
        return RECIPES["best"](options)
    techs = list(techniques)
    # A recipe name (e.g. `--use best`) resolves to a named assembly from builder.py.
    # Recipes are whole assemblies, not ladder rungs, so they are cited alone.
    if len(techs) == 1 and techs[0] in RECIPES:
        return RECIPES[techs[0]](options)
    return _from_techniques(options, techs)


__all__ = ["build_portfolio", "TECHNIQUES", "PRODUCERS", "WRAPPERS"]
