"""genaut/gen/shape.py — the parametric shape descriptor for the census.

A Shape fixes the three axes of the enumeration and derives the slot model from
them: the generator-id space [0, N), the per-slot guard alphabet, the acceptance
marksets, and the id<->combo bijection behind each survivor's name <tag>_<id>.hoa.
Pure (stdlib only) — the Spot realisation of a combo lives in build.py.

See algorithm.md for the model; the short of it:
  Shape(n, k, c)                 n states, k APs, c acceptance sets
  Markset = subsets of range(c)            (c=0 -> {()}, so acceptance is `t`)
  Slot    = (src, dst, markset)            |Slots| = n^2 * 2^c
  Guards_k = truth-table bitmasks over the 2^k minterms, guard 0 = absent
             |Guards_k| = 2^(2^k);  k=1 -> (0=absent, 1=!a, 2=a, 3=true)
  N        = |Guards_k| ** |Slots|
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import List, Tuple

Markset = Tuple[int, ...]               # a subset of the acceptance colours
Slot = Tuple[int, int, Markset]         # (src, dst, markset)


def guard_alphabet(naps: int) -> Tuple[int, ...]:
    """The guard codes for `naps` APs: truth-table bitmasks 0..2^(2^naps)-1 over
    the 2^naps minterms (the letters of 2^AP; bit m set <=> letter m is in the
    guard). A guard is thus any subset of the letters; guard 0 is the empty union
    = the all-false function = "edge absent". Realised for any naps>=0 — the
    letters come from one minterm walk (build._minterm_bdds, the APBDDIterator
    idea); naps=0 gives (0, 1): the one-letter alphabet, absent or `true`."""
    if naps < 0:
        raise ValueError(f"naps must be >= 0, got {naps}")
    return tuple(range(1 << (1 << naps)))     # naps=1 -> (0,1,2,3): absent,!a,a,true


def acc_marksets(nacc: int) -> Tuple[Markset, ...]:
    """All acceptance marksets — subsets of range(nacc) — ordered by increasing
    size then lexicographically. nacc=0 -> ((),) (a single unmarked slot, so the
    acceptance is `t`); nacc=1 -> ((), (0,)) — unmarked before marked."""
    out: List[Markset] = []
    for size in range(nacc + 1):
        out.extend(itertools.combinations(range(nacc), size))
    return tuple(out)


@dataclass(frozen=True)
class Shape:
    nstates: int
    naps: int
    nacc: int

    @property
    def tag(self) -> str:
        return f"{self.nstates}state{self.naps}ap{self.nacc}acc"

    @property
    def guards(self) -> Tuple[int, ...]:
        return guard_alphabet(self.naps)

    @property
    def marksets(self) -> Tuple[Markset, ...]:
        return acc_marksets(self.nacc)

    @property
    def slots(self) -> Tuple[Slot, ...]:
        """The edge slots, in id order: src outer, then dst, then markset."""
        return tuple(
            (src, dst, ms)
            for src in range(self.nstates)
            for dst in range(self.nstates)
            for ms in self.marksets)

    @property
    def num_combos(self) -> int:
        return len(self.guards) ** len(self.slots)

    @property
    def id_width(self) -> int:
        """Zero-pad width for the generator id in filenames: just enough digits for
        the largest id (num_combos-1), no more — so 1state1ap0acc (N=4) pads to 1
        digit, 2state1ap1acc (N=65536) to 5."""
        return len(str(self.num_combos - 1))

    def combo_at(self, index: int) -> Tuple[int, ...]:
        """The guard tuple at generator id `index` (one guard code per slot), in the
        same order the driver visits — itertools.product, last slot fastest. The
        inverse of "which combo produced <tag>_<index>.hoa"."""
        n = self.num_combos
        if not 0 <= index < n:
            raise IndexError(f"index {index} out of range [0, {n}) for {self.tag}")
        return next(itertools.islice(
            itertools.product(self.guards, repeat=len(self.slots)), index, index + 1))
