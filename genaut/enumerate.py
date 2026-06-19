"""
genaut/enumerate.py — exhaustively generate 2-state / 1-AP / 1-acc-set TGBA.

Slot model (full, symmetric; q0 is the initial state):
  for every ordered pair (src, dst) in {q0,q1}^2 and every acceptance value
  mark in {unmarked, marked} there is ONE edge slot whose guard is drawn from
  {0, a, !a, 1}, with 0 meaning "edge absent". That is 2*2*2 = 8 slots, each 4
  choices -> 4**8 = 65536 raw automata. With one AP this slot set is fully
  general (a marked `a` plus an unmarked `!a` self-loop is a distinct automaton;
  `a`-marked + `!a`-marked = `1`-marked, so parallel edges are covered too).

Pipeline (generation only — dedup is a later, separate step):
  build each automaton -> ONE spot postprocess(Small, Generic family) pass ->
  append the result to a single multi-automaton HOA stream.

Usage:
  python3 genaut/enumerate.py [LIMIT]      # LIMIT: smoke-test the first N combos
Output:
  genaut/raw/aut_NNNNN.hoa   (one HOA automaton per generated case)
"""
from __future__ import annotations

import hashlib
import itertools
import os
import sys
from typing import List, Optional, Set, Tuple

import spot
import buddy

OUT_DIR = os.path.join(os.path.dirname(__file__), "raw")

# Guard alphabet over the single AP "a": (label, kind) where kind drives the bdd.
#   "0" -> edge absent (skipped)   "1" -> bddtrue   "a"/"na" -> the two literals
GUARDS: Tuple[str, ...] = ("0", "1", "a", "na")

# The 8 edge slots: (src, dst, marked).
SLOTS: List[Tuple[int, int, bool]] = [
    (src, dst, mark)
    for src in (0, 1)
    for dst in (0, 1)
    for mark in (False, True)
]


def build_aut(combo: Tuple[str, ...], bdict: "spot.bdd_dict") -> "spot.twa_graph":
    """Build one raw TGBA from a length-8 tuple of guard labels (one per slot)."""
    aut = spot.make_twa_graph(bdict)
    ap = aut.register_ap("a")
    aut.set_generalized_buchi(1)
    aut.new_states(2)
    aut.set_init_state(0)

    va = buddy.bdd_ithvar(ap)
    na = buddy.bdd_nithvar(ap)
    cond = {"1": buddy.bddtrue, "a": va, "na": na}

    for (src, dst, mark), g in zip(SLOTS, combo):
        if g == "0":
            continue
        aut.new_edge(src, dst, cond[g], [0] if mark else [])
    return aut


def make_postprocessor() -> "spot.postprocessor":
    p = spot.postprocessor()
    p.set_type(spot.postprocessor.Generic)   # keep the acceptance family
    p.set_pref(spot.postprocessor.Small)
    p.set_level(spot.postprocessor.High)
    return p


def main(limit: Optional[int]) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    bdict = spot.make_bdd_dict()
    post = make_postprocessor()

    combos = itertools.product(GUARDS, repeat=len(SLOTS))
    seen: Set[str] = set()                 # md5 of every distinct exported HOA
    total = 0
    written = 0
    for i, combo in enumerate(combos):
        if limit is not None and i >= limit:
            break
        total += 1
        content = post.run(build_aut(combo, bdict)).to_str("hoa") + "\n"
        digest = hashlib.md5(content.encode()).hexdigest()
        if digest in seen:                 # byte-identical to an earlier id -> drop
            continue
        seen.add(digest)
        path = os.path.join(OUT_DIR, f"aut_{i:05d}.hoa")
        with open(path, "w") as out:
            out.write(content)
        written += 1
        if total % 5000 == 0:
            print(f"  ... {total} scanned, {written} kept", file=sys.stderr)

    print(f"scanned {total} combos, kept {written} distinct -> {OUT_DIR}/aut_NNNNN.hoa")


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(lim)
