"""
aut2ltl.daisystar — the rejecting length-1 star-hub combinator Translator.

`Daisystar(child)` peels the initial state's SCC when it is a **rejecting**
length-1 star hub (a hub with petal self-loops, hub-stems, and one-hop spokes
that may themselves exit `C`): the *reachability* dual of `daisy2`. Since no run
staying in `C` forever accepts, `STAY∞ = false` (sound by construction), and the
language is the pure `LEAVE` least-fixpoint — finitely many stay-moves, then an
exit to a child (a hub-stem, or a **spoke-exit** `E_s ∧ X(G_s U (h_k ∧ X φ_k))`).
It adopts the candidate only if a Spot oracle confirms language-equivalence, and
declines otherwise. Always sound. See algorithm.md.

Public entry: `Daisystar`.
"""

from .daisystar import Daisystar

__all__ = ["Daisystar"]
