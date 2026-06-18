"""
aut2ltl.portfolio — the composition layer (combinators) over the engines.

A `Language` is translated by the shipped default — the `best` recipe
(`builder.best`): a strength/acceptance decomposition over a self-loop daisy peel
flooring on the kr cascade. Every piece is a Translator (`Language -> LTLResult`);
the engine (`aut2ltl.bls`) and the (de)composition approaches (`aut2ltl.daisy`,
`aut2ltl.partscc`, `aut2ltl.decomp`) stay PEERS importing only the contract floor.

`build_portfolio(options, techniques)` (`portfolio/build.py`) is the single entry:

    techniques is None   ⇒ the shipped default, RECIPES["best"]
    a recipe name        ⇒ that named assembly  (e.g. --use best)
    a list of technique  ⇒ the cited-technique ladder (research/CLI path)
    names

See `build.py` for the cited-technique vocabulary and `builder.py` for the recipes.
"""
from __future__ import annotations

from aut2ltl.first_success import first_success
from aut2ltl.options import Options
from aut2ltl.bls.options import KR_OPTIONS
from .build import build_portfolio, TECHNIQUES
from .builder import RECIPES

# One shared default Options threaded through the whole graph: the object graph IS
# the config graph. Seeded from the kr contract (the only knobs the modern recipes
# read); a caller wanting a variant rebuilds with `build_portfolio` + a cited
# technique set or a cloned Options (the A/B move).
_options = Options.from_specs(KR_OPTIONS)

__all__ = [
    "build_portfolio",
    "TECHNIQUES",
    "RECIPES",
    "first_success",
]
