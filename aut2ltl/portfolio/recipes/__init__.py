"""
aut2ltl.portfolio.recipes — the named assemblies (`RECIPES`), one module per recipe.

A *recipe* is a builder `Options -> Translator` that wires the building blocks
(`portfolio/builder.py`: `bls`, `core`, `daisy`, `daisy_pair`, `daisy_pair_inv`) into
a useful whole. Each recipe lives in its own module here; this `__init__` aggregates
them into the `RECIPES` registry that `build_portfolio` resolves for `--use <name>`.

Adding a recipe is two lines: drop `recipes/<name>.py` defining a builder, then list
it in `RECIPES` below. The CLI (`--use <name>`) and the survey/benchmark scripts honor
it automatically — they read this registry, nothing else to wire.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from .best import best
from .best_daisy2 import best_daisy2
from .best_inv import best_inv
from .best_inv_loop import best_inv_loop
from .best_inv_all import best_inv_all
from .cake import cake
from .cakeds import cakeds
from .cakedsdet import cakedsdet
from .nobls import nobls
from .deep_nobls import deep_nobls
from .deep_nobls_memo import deep_nobls_memo
from .deep_nobls_sort import deep_nobls_sort
from .deep_nobls_sort_decomp import deep_nobls_sort_decomp
from .roundtrip import roundtrip
from .roundtrip_best import roundtrip_best_recipe
from .roundtrip_decomp import roundtrip_decomp_recipe

# Public recipe names → builders. `build_portfolio` resolves `--use <name>` here.
RECIPES: Dict[str, Callable[[Optional[Options]], Translator]] = {
    "best": best,
    "best_daisy2": best_daisy2,
    "best_inv": best_inv,
    "best_inv_loop": best_inv_loop,
    "best_inv_all": best_inv_all,
    "cake": cake,
    "cakeds": cakeds,
    "cakedsdet": cakedsdet,
    "nobls": nobls,
    "deep_nobls": deep_nobls,
    "deep_nobls_memo": deep_nobls_memo,
    "deep_nobls_sort": deep_nobls_sort,
    "deep_nobls_sort_decomp": deep_nobls_sort_decomp,
    "roundtrip": roundtrip,
    "roundtrip_best": roundtrip_best_recipe,
    "roundtrip_decomp": roundtrip_decomp_recipe,
}

# The shipped default — the assembly used when no `--use` is given (the CLI/build
# entrypoint resolves the empty case to the name `"default"`, and `--use default`
# names it explicitly). This single alias IS the default pointer: re-point it to one
# of the recipes above to ship a different default; nothing else in the CLI, build,
# or survey changes.
RECIPES["default"] = RECIPES["deep_nobls"]

__all__ = ["RECIPES", "best", "best_daisy2", "best_inv", "best_inv_loop",
           "best_inv_all", "cake", "cakeds", "cakedsdet", "nobls", "deep_nobls",
           "deep_nobls_memo", "deep_nobls_sort", "deep_nobls_sort_decomp",
           "roundtrip", "roundtrip_best_recipe", "roundtrip_decomp_recipe"]
