"""Drive daisystar on a single hand-crafted input and report what happened.

Usage:  python3 tests/daisystar/probe_daisystar.py '<LTL formula>' [-v]

Builds the Language from the formula, runs Daisystar with a `Daisy(decline)`
child (enough to label a trivial true-sink stem target), and prints: the
star-partition shape (petals / spokes / hub-stems, and each spoke's exits),
whether the initial SCC is rejecting (the regime gate), the candidate LEAVE
formula, and whether the Spot gate accepted it — with a containment witness in
each direction when the candidate is wrong, so we can see *why*.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import spot                                                         # noqa: E402

from aut2ltl.language import Language                               # noqa: E402
from aut2ltl.result import decline                                 # noqa: E402
from aut2ltl.daisy.daisy import Daisy                              # noqa: E402
from aut2ltl.daisystar.daisystar import Daisystar, build_leave     # noqa: E402
from aut2ltl.daisystar.shape import star_partition, reroot         # noqa: E402
from aut2ltl.simplify_ltl import Simplify                          # noqa: E402


def main(arg: str) -> None:
    # An existing path is loaded as a HOA automaton; otherwise arg is an LTL
    # formula. The HOA route lets us probe hand-built adversarial stars (e.g.
    # tests/fixtures/daisystar_loose.hoa) the LTL front end would not produce.
    lang = Language.of(spot.automaton(arg)) if os.path.exists(arg) else Language.of_ltl(arg)
    aut = lang.tgba()
    h = aut.get_init_state_number()
    si = spot.scc_info(aut)
    print(f"input      : {arg}")
    print(f"tgba       : {aut.num_states()} states, "
          f"{aut.acc().num_sets()} acc sets, init {h}")
    print(f"init SCC    : rejecting={si.is_rejecting_scc(si.scc_of(h))}")
    if "-v" in sys.argv[2:]:
        print("--- edges (src -[guard]{marks}-> dst) ---")
        for s in range(aut.num_states()):
            for e in aut.out(s):
                g = spot.bdd_to_formula(e.cond, aut.get_dict())
                print(f"  {e.src} -[{g}]{set(e.acc.sets())}-> {e.dst}")

    parts = star_partition(aut, h)
    if parts is None:
        print("shape      : NOT a length-1 star hub  -> daisystar declines")
        return
    petals, spokes, hub_stems = parts
    print(f"shape      : {len(petals)} petals, {len(spokes)} spokes, "
          f"{len(hub_stems)} hub-stems")
    for sp in spokes:
        print(f"  spoke s={sp.state}: E={sp.entry}  G={sp.body}  R={sp.ret}  "
              f"stems={[(str(g), d) for g, d in sp.stems]}")

    child = Daisy(decline)
    res = Simplify(Daisystar(child), "lo")(lang)
    print(f"status     : {res.status.value}   technique={res.technique_str()}")
    if res.diagnosis:
        print(f"diagnosis  : {res.diagnosis}")
    if res.ok:
        print(f"formula    : {res.formula}")
    else:
        # Show the full rejected candidate + witnesses to study the failure.
        child_of = {}
        dsts = [d for _, d in hub_stems] + [d for sp in spokes for _, d in sp.stems]
        for dst in dict.fromkeys(dsts):
            child_of[dst] = child(Language.of(reroot(aut, dst))).formula
        cand = build_leave(petals, spokes, hub_stems, child_of)
        print(f"candidate  : {cand}")
        try:
            ca = cand.translate("GeneralizedBuchi", "Small", "High")
            extra = ca.intersecting_word(spot.complement(aut))   # cand \ input
            miss = aut.intersecting_word(spot.complement(ca))    # input \ cand
            print(f"  cand \\ input (too loose) : {extra}")
            print(f"  input \\ cand (too tight) : {miss}")
        except Exception as e:
            print(f"  (witness probe failed: {e})")


if __name__ == "__main__":
    main(sys.argv[1])
