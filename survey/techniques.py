"""survey.techniques — resolve the requested --use set.

survey is agnostic to technique VALUES: requested names are passed through to
the front end opaquely (never enumerated or validated here). The sole token this
module interprets is `all`, which must expand — via runtime discovery from the
portfolio registry — to every available technique. No technique name is ever
hardcoded in this package.

Bones only — `all` discovery is a TODO (see survey/README.md).
"""
from __future__ import annotations

# TODO: resolve(uses: list[str]) -> list[Optional[str]]
#       []        -> [None]            (the default technique only)
#       [a, b]    -> [a, b]            (pass-through, one run each)
#       ['all']   -> discover_all()    (NOT YET: needs registry discovery)
