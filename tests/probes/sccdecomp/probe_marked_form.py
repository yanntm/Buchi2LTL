"""Probe the 'right form' for accepting-SCC decomposition: mark-based acceptance.

restrict_marks(clear outside C) isolates C only when acceptance is Inf-based with
>= 1 set; the all-accepting `t` condition (0 sets) breaks it. Compare ways to
materialize `t` into a marked form (so an SCC with no marks reads as rejecting):
  - spot.postprocess(aut, "Buchi")        (does it mark a `t` automaton?)
  - manual: every edge gets set 0, acceptance Inf(0)
on the input's tgba, reporting num_sets and language preservation. (≤15s)

    python3 tests/sccdecomp/probe_marked_form.py 'Ga | Gb'
"""
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import spot  # noqa: E402

from aut2ltl.language import Language  # noqa: E402


def _materialize(aut: "spot.twa_graph") -> "spot.twa_graph":
    """Mark every edge with a fresh Büchi set 0; acceptance becomes Inf(0).
    Language-preserving when the input was all-accepting (`t`)."""
    out = spot.make_twa_graph(aut.get_dict())
    out.copy_ap_of(aut)
    out.set_acceptance(1, "Inf(0)")
    for _ in range(aut.num_states()):
        out.new_state()
    full = spot.mark_t([0])
    for s in range(aut.num_states()):
        for e in aut.out(s):
            out.new_edge(s, e.dst, e.cond, full)
    out.set_init_state(aut.get_init_state_number())
    return out


def _show(tag: str, a: "spot.twa_graph", base: "spot.twa_graph") -> None:
    print(f"  {tag:13} states={a.num_states()} sets={a.num_sets()} acc={a.acc()}"
          f"  EQUIV={spot.are_equivalent(a, base)}")


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    f = spot.formula(argv[1])
    print(f"FORMULA: {f}")
    a = Language.of_ltl(f).tgba()
    print(f"  tgba          states={a.num_states()} sets={a.num_sets()} acc={a.acc()}")
    _show("Buchi", spot.postprocess(a, "Buchi"), a)
    _show("materialized", _materialize(a), a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
