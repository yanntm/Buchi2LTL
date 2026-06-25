"""
genaut/enumerate.py — exhaustively generate 2-state / 1-AP / 1-acc-set TGBA.

Slot model (full, symmetric; q0 is the initial state):
  for every ordered pair (src, dst) in {q0,q1}^2 and every acceptance value
  mark in {unmarked, marked} there is ONE edge slot whose guard is drawn from
  {0, a, !a, 1}, with 0 meaning "edge absent". That is 2*2*2 = 8 slots, each 4
  choices -> 4**8 = 65536 raw automata. With one AP this slot set is fully
  general (a marked `a` plus an unmarked `!a` self-loop is a distinct automaton;
  `a`-marked + `!a`-marked = `1`-marked, so parallel edges are covered too).

Pipeline (all dedup is in-memory, PRE-write -- a twin is never built into a file):
  build each automaton -> ONE spot postprocess(Small, Generic family) pass ->
  drop byte-identical results (md5, first generator-id wins) -> drop AP-canonical
  twins (key = polarity o names, from tests/benchmark/normalize; only the
  byte-distinct survivors pay this cost) -> write the rest, one HOA per file.
  65536 combos collapse to 1845 byte-distinct, then 929 AP-canonical survivors.
  The AP-canonical key is reused verbatim from the shared normalize tool, so the
  same pre-process applies to any future family/shape regen, not just this census.

Each surviving file keeps its GENERATOR ID in the name (aut_<index>.hoa), so the
exact raw automaton is reproducible from the index alone via `aut_at(index, ...)`
(see genaut/probe_post.py).

Usage:
  python3 genaut/enumerate.py [LIMIT]      # LIMIT: smoke-test the first N combos
Output:
  genaut/raw/aut_NNNNN.hoa   (one HOA automaton per surviving case)
"""
from __future__ import annotations

import hashlib
import itertools
import os
import sys
from typing import Callable, List, Optional, Set, Tuple

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

# Total raw combos in the enumeration (the generator-id space): 4**8 = 65536.
NUM_COMBOS: int = len(GUARDS) ** len(SLOTS)


def combo_at(index: int) -> Tuple[str, ...]:
    """The length-8 guard tuple at generator position `index` — the same order
    the main loop visits (itertools.product over GUARDS, rightmost slot fastest).
    The inverse of "which combo produced aut_<index>.hoa"."""
    if not 0 <= index < NUM_COMBOS:
        raise IndexError(f"index {index} out of range [0, {NUM_COMBOS})")
    return next(itertools.islice(
        itertools.product(GUARDS, repeat=len(SLOTS)), index, index + 1))


def aut_at(index: int, bdict: "spot.bdd_dict") -> "spot.twa_graph":
    """Rebuild the RAW automaton (pre-postprocess) for generator id `index`."""
    return build_aut(combo_at(index), bdict)


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


# The single reduction pass, via the same spot.postprocess string convenience the
# tool uses for input cleanup (aut2ltl/language.py::_clean) — (type, level, pref).
# Generic keeps the acceptance family; Small is the structural reducer (NOT the
# `deterministic` pref, so universality is not decided — see README).
POST_ARGS = ("generic", "high", "small")


def reduce_aut(aut: "spot.twa_graph") -> "spot.twa_graph":
    return spot.postprocess(aut, *POST_ARGS)


def _ap_canonical_key() -> "Callable[[str], str]":
    """The shared AP-canonical key (polarity o names) from the normalize package,
    loaded by path since it lives under tests/. Used to fold the `a <-> !a`
    polarity / AP-rename twins that byte-identity cannot see -- here applied ON
    THE FLY (pre-write), so a twin is never built into a file in the first place.
    Reused verbatim from the shared tool, so it carries to any future regen."""
    repo_root = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, os.path.join(repo_root, "tests", "benchmark", "normalize"))
    from dedup import default_key                          # noqa: E402
    return default_key


def main(limit: Optional[int]) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    bdict = spot.make_bdd_dict()
    ap_key = _ap_canonical_key()

    combos = itertools.product(GUARDS, repeat=len(SLOTS))
    seen_md5: Set[str] = set()             # cheap pre-filter: byte-identical HOA
    seen_key: Set[str] = set()             # AP-canonical key (polarity o names)
    total = 0
    written = 0
    folded = 0                             # md5-distinct but AP-canonical twins
    for i, combo in enumerate(combos):
        if limit is not None and i >= limit:
            break
        total += 1
        content = reduce_aut(build_aut(combo, bdict)).to_str("hoa") + "\n"
        digest = hashlib.md5(content.encode()).hexdigest()
        if digest in seen_md5:             # byte-identical to an earlier id -> drop
            continue
        seen_md5.add(digest)
        key = ap_key(content)              # only the ~1845 md5-survivors pay this
        if key in seen_key:                # AP-canonical twin of an earlier id -> drop
            folded += 1
            continue
        seen_key.add(key)
        path = os.path.join(OUT_DIR, f"aut_{i:05d}.hoa")
        with open(path, "w") as out:
            out.write(content)
        written += 1
        if total % 5000 == 0:
            print(f"  ... {total} scanned, {written} kept", file=sys.stderr)

    print(f"scanned {total} combos, kept {written} AP-canonical distinct "
          f"({len(seen_md5)} byte-distinct, {folded} polarity/name twins folded "
          f"pre-write) -> {OUT_DIR}/aut_NNNNN.hoa")


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(lim)
