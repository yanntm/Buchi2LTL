"""
aut2ltl.daisy2 — the length-1 star-hub combinator Translator.

`Daisy2(child)` peels the initial state's SCC when it is a **length-1 star hub**
(a hub with petal self-loops, stem exits, and one-hop spokes), generalizing
`daisy` by one level: each spoke is itself a one-state daisy. It emits the daisy
production lifted from letters to moves and adopts the candidate only if a Spot
oracle confirms language-equivalence (the closed move-level form is not yet
solved — see algorithm2.md), declining otherwise. Always sound. Defined against
the Translator contract; imports only `spot`, the floor (`aut2ltl.language`,
`aut2ltl.result`), its own `shape` helpers, and `reroot` reused from `daisy`.

Public entry: `Daisy2`. See algorithm2.md for the construction.
"""

from .daisy2 import Daisy2

__all__ = ["Daisy2"]
