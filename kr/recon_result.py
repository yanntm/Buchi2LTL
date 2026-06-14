"""
kr/recon_result.py — the portfolio result struct.

kr has become a PORTFOLIO: a given automaton is reconstructed by whichever
method wins at each node of the decompose-and-recombine dispatch — the
buchi2ltl gate, an AND/OR strength/acceptance split, or one of the leaf
acceptance-dispatch forms (acc / weak / buchi / cobuchi / the Muller-DNF
cascade `bls`). The bare `spot.formula` return hid which method fired, so the
top-level entry now returns this struct, carrying the formula plus the SET of
methods that contributed.

`.technique` is a set (deduped) accumulated down the dispatch tree:
  * 'and<n>' / 'or<n>'           — a boolean split into n pieces occurred at some
                                   node (n = number of conjuncts / disjuncts);
                                   subsumes the old `split_report` side channel;
  * 'sl' / 't2' / 'f2'           — the buchi2ltl gate produced a node (its own
                                   technique tokens, split on '+');
  * 'acc' / 'weak' / 'buchi' /
    'cobuchi' / 'bls'            — the leaf acceptance-dispatch method
                                   (`bls` = the general Muller-DNF cascade);
  * 'base'                       — a custom (non-default) reconstruct callable
                                   produced a leaf (probes/tests).

MT-safe by construction: the accumulator is a per-call local threaded by
reference through the dispatch, never a module-level/global recorder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Set


@dataclass
class ReconResult:
    """A reconstructed formula DAG plus the set of methods that built it."""
    formula: "spot.formula"
    technique: Set[str] = field(default_factory=set)

    def technique_str(self) -> str:
        """Stable '+'-joined rendering (sorted) for logs/surveys."""
        return "+".join(sorted(self.technique)) if self.technique else "-"
