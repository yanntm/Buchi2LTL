"""Feed PartScc an embedded terminal SCC after rerooting (what a labeler would do).

Many formulas have their terminal SCC behind a prefix/init state, so the whole
TGBA is not a single SCC and the pure leaf declines. This probe simulates the
upstream reroot: find a terminal SCC of size >= 2, build the sub-automaton rooted
at one of its states (= the isolated 'stay forever' language), wrap it as
Language.of, and run PartScc on THAT. Single input, one formula per call (≤15s):

    python3 tests/partscc/probe_reroot.py 'G((!p & X p) | (p & X !p))'
"""
import sys
from typing import List, Optional

import spot  # noqa: E402

from aut2ltl.language import Language  # noqa: E402
from aut2ltl.partscc import PartScc  # noqa: E402

def _terminal_scc_state(aut: "spot.twa_graph") -> Optional[int]:
    """One state of a terminal (escape-free) SCC of size >= 2, or None."""
    si = spot.scc_info(aut)
    for scc in range(si.scc_count()):
        states = [int(s) for s in si.states_of(scc)]
        if len(states) < 2:
            continue
        terminal = all(si.scc_of(e.dst) == scc for st in states for e in aut.out(st))
        if terminal:
            return states[0]
    return None

def _reroot(aut: "spot.twa_graph", state: int) -> "spot.twa_graph":
    sub = spot.automaton(aut.to_str("hoa"))
    sub.set_init_state(state)
    sub.purge_unreachable_states()
    return sub

def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    f = spot.formula(argv[1])
    print(f"FORMULA : {f}")

    tgba = Language.of_ltl(f).tgba()
    st = _terminal_scc_state(tgba)
    if st is None:
        print("RESULT  : no terminal SCC of size >= 2 in the TGBA")
        return 0

    sub = _reroot(tgba, st)
    si = spot.scc_info(sub)
    print(f"REROOTED: state {st} -> {sub.num_states()} states, {si.scc_count()} SCC(s)")

    res = PartScc()(Language.of(sub))
    if not res.ok:
        print(f"RESULT  : DECLINED ({res.diagnosis})")
        return 0
    g = res.formula
    print(f"TECHNIQUE: {sorted(res.technique)}")
    print(f"RESULT  : {g}")
    # The reconstructed fragment must match the rerooted sub-language.
    eq = spot.are_equivalent(sub, spot.translate(g))
    print(f"EQUIV   : {eq}")
    return 0 if eq else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
