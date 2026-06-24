"""
aut2ltl.bls.definability.witness — extract non-LTL witness material.

On a non-LTL language the transition monoid carries a non-trivial group; this
package makes it concrete. `extract_witness` returns the period word `v` and period
`p` of the counting family `(u, v, x, p)` (stage 1: `v`, `p`); the family completion
and the verifier are separate. See algorithm.md.
"""

from .witness import Witness, extract_witness

__all__ = ["Witness", "extract_witness"]
