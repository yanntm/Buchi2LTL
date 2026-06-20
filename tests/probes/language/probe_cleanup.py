"""Probe the Language-factory cleanup wrapper: spot.postprocess(generic, low, any).

Tests whether the gentlest postprocess config — Generic (keep acceptance type),
Low (simulation only), Any (no size preference) — already does the basic cleanup
we want: purge unreachable/dead states AND drop unused atomic propositions, so we
need no deeper API. Rerooting a formula's automaton to its terminal SCC is the
realistic source of unused APs (the prefix's atoms go dead). Prints before/after
and whether an explicit remove_unused_ap() would do anything MORE; checks language
equivalence. Single formula per call (≤15s):

    python3 tests/language/probe_cleanup.py 'a U G(p -> X q)'
"""
import sys
from typing import List, Optional

import spot  # noqa: E402

def _aps(aut: "spot.twa_graph") -> List[str]:
    return sorted(str(x) for x in aut.ap())

def _terminal_scc_state(aut: "spot.twa_graph") -> Optional[int]:
    si = spot.scc_info(aut)
    for scc in range(si.scc_count()):
        states = [int(s) for s in si.states_of(scc)]
        if len(states) < 2:
            continue
        if all(si.scc_of(e.dst) == scc for st in states for e in aut.out(st)):
            return states[0]
    return None

def _show(tag: str, aut: "spot.twa_graph") -> None:
    print(f"  {tag:18} states={aut.num_states():2}  aps={_aps(aut)}  acc={aut.acc()}")

def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    f = spot.formula(argv[1])
    print(f"FORMULA : {f}")
    base = f.translate()
    _show("base", base)

    st = _terminal_scc_state(base)
    if st is None:
        print("  (no terminal SCC >= 2; testing cleanup on the base directly)")
        sub = base
    else:
        sub = spot.automaton(base.to_str("hoa"))
        sub.set_init_state(st)
        sub.purge_unreachable_states()
        _show("rerooted (raw)", sub)

    # Snapshot the AP lists immediately — remove_unused_ap() mutates the shared
    # bdd_dict, so reading clean.ap() after clean2's call would be misleading.
    clean = spot.postprocess(sub, "generic", "low", "any")
    clean_aps = _aps(clean)
    _show("generic/low/any", clean)
    eq = spot.are_equivalent(sub, clean)

    clean2 = spot.postprocess(sub, "generic", "low", "any")
    clean2.remove_unused_ap()
    clean2_aps = _aps(clean2)
    _show("+remove_unused_ap", clean2)

    dropped = sorted(set(clean_aps) - set(clean2_aps))
    print(f"  AP dropped ONLY by explicit remove_unused_ap: {dropped or 'none'}")
    print(f"  => low alone removes unused APs: {not dropped}")
    print(f"  EQUIV(sub, clean): {eq}")
    return 0 if eq else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
