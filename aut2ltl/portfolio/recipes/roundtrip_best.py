"""roundtrip_best — the never-regress round trip, a shared seed, three bricks.

The combo of `roundtrip_status.md` direction 3, built from three bricks each with
one concern:

    best_of([ Memo(C), Roundtrip(Memo(C)) ])

- `Roundtrip` — the pure re-presentation move (no size judgment of its own);
- `best_of`  — the choice (keep whichever result the comparator prefers);
- `Memo`     — the only brick that knows about sharing.

One shared `Memo(child)` feeds both arms, so `child` runs once on the seed
language: `Roundtrip`'s seed step calls the same `Memo` the plain arm calls, a
cache hit, so only the relabel on the *re-presented* language is genuinely paid.

Never-regress: the plain arm is the baseline and the round trip displaces it only
when `best_of`'s comparator says it wins. Which comparator that is belongs to
`best_of` (and the caller), not to this brick — the brick neither knows nor
checks its context. That purity is what keeps the combinator algebra sound by
construction.
"""
from __future__ import annotations

from typing import Optional

from aut2ltl.translator import Translator
from aut2ltl.options import Options
from aut2ltl.best_of import best_of
from aut2ltl.memo import Memo
from aut2ltl.roundtrip import Roundtrip
from .cakedsdet import cakedsdet


def roundtrip_best(child: "Translator", *, name: str = "roundtrip_best") -> "Translator":
    """The never-regress round-trip combo over `child`: keep the better of the
    plain labeling and the round-tripped one, sharing a single `Memo(child)` so
    `child` runs once on the seed language. Pure wiring of three bricks — `Memo`
    (sharing), `Roundtrip` (re-presentation), `best_of` (choice); the size
    comparator is `best_of`'s concern, not this brick's."""
    m = Memo(child)
    return best_of([m, Roundtrip(m)], name=name)


def roundtrip_best_recipe(options: Optional[Options] = None) -> "Translator":
    """`--use roundtrip_best`: the combo over `cakedsdet` (the current best). The
    never-regress fix to the naive `roundtrip` recipe — kept alongside it for
    A/B (`roundtrip` returns the relabel unconditionally and can regress)."""
    return roundtrip_best(cakedsdet(options))


__all__ = ["roundtrip_best", "roundtrip_best_recipe"]
