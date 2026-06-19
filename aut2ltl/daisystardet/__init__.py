"""
aut2ltl.daisystardet — the deterministic anchored read-off combinator Translator.

`DaisystarDet(child)` peels the initial state's SCC when it is **rejecting** with a
**deterministic L-partition** (each entry-letter set tight and pairwise disjoint —
`partscc`'s input-determinizing condition) and at least one exit. It then emits a
**flat, fixpoint-free, exact** label — `partscc`'s transition law run `U`-to-an-exit
instead of `G`-with-fairness (the reachability dual). Determinism makes the run
unique, so the pointwise law equals run legality and the read-off is exact; it is
the sound, exact replacement for `daisystar`'s flat `LEAVE` and is **not** restricted
to length-1 stars. It still adopts under a Spot equivalence gate (declining on an
unproven surprise) and declines when the precondition fails. Always sound.

Imports only `spot`/`buddy`, the floor (`aut2ltl.language`, `aut2ltl.result`), its
own `shape` helpers, and `reroot` reused from `daisy`.

Public entry: `DaisystarDet`. See algorithm.md for the construction.
"""

from .daisystardet import DaisystarDet

__all__ = ["DaisystarDet"]
