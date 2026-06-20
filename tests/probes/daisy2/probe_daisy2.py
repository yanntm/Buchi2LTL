"""Drive daisy2 on a single hand-crafted input and report what happened.

Usage:  python3 tests/daisy2/probe_daisy2.py '<LTL formula>'

Builds the Language from the formula, runs Daisy2 with a declining child (so
stems, if any, are not resolved -- keep examples to pure star SCCs for now),
and prints: the star-partition shape, the candidate formula, whether the Spot
gate accepted it (success) or rejected it (decline), and a containment witness
when the candidate is wrong so we can see *why*.
"""
import sys

import spot

from aut2ltl.language import Language
from aut2ltl.result import decline
from aut2ltl.daisy2.daisy2 import Daisy2, build_candidate
from aut2ltl.daisy2.shape import star_partition
from aut2ltl.simplify_ltl import Simplify


def main(arg: str) -> None:
    lang = Language.of_ltl(arg)
    aut = lang.tgba()
    h = aut.get_init_state_number()
    print(f"input      : {arg}")
    print(f"tgba       : {aut.num_states()} states, "
          f"{aut.acc().num_sets()} acc sets, init {h}")
    if "-v" in sys.argv[2:]:
        print("--- edges (src -[guard]{marks}-> dst) ---")
        for s in range(aut.num_states()):
            for e in aut.out(s):
                g = spot.bdd_to_formula(e.cond, aut.get_dict())
                print(f"  {e.src} -[{g}]{set(e.acc.sets())}-> {e.dst}")

    parts = star_partition(aut, h)
    if parts is None:
        print("shape      : NOT a length-1 star hub  -> daisy2 declines")
        return
    petals, spokes, stems = parts
    print(f"shape      : {len(petals)} petals, {len(spokes)} spokes, "
          f"{len(stems)} stems")
    for sp in spokes:
        print(f"  spoke s={sp.state}: E={sp.entry}  G={sp.body}  R={sp.ret}")
        print(f"    entries={[(str(g), set(M)) for g, M in sp.entries]}  "
              f"rets={[(str(g), set(M)) for g, M in sp.rets]}")

    # Chain a low LTL simplifier onto the result for readability; transparent on
    # declines, and it runs after daisy2's validity gate so it only prettifies an
    # already-confirmed formula.
    res = Simplify(Daisy2(decline), "lo")(lang)
    print(f"status     : {res.status.value}   technique={res.technique_str()}")
    if res.diagnosis:
        print(f"diagnosis  : {res.diagnosis}")
    if res.ok:
        print(f"formula    : {res.formula}")
    else:
        # Show the FULL rejected candidate and witnesses, to study the failure.
        # (Stems unresolved here -> keep examples to pure star SCCs, children=[].)
        m = aut.acc().num_sets()
        cand = build_candidate(petals, spokes, stems, [], m)
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
