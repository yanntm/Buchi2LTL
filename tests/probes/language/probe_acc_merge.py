"""What does each postprocess level (low/medium/high) do for our basic cleanups?

Sweeps spot.postprocess(generic, <level>, any) over three phenomena, all
language-preserving and acceptance-type-preserving under Generic:
  1. redundant acc sets  — Inf(0)&Inf(1) with both sets on every edge: does the
     level collapse them to one?
  2. unused AP           — an AP no edge mentions: does the level drop it, or is an
     explicit remove_unused_ap() still needed?
  3. state reduction     — simulation-equivalent states: does the level merge them?
Prints sets / aps / states before and after each level, with an equivalence check.
No args (self-contained, ≤15s):

    python3 tests/language/probe_acc_merge.py
"""
from typing import List

import spot  # noqa: E402

_LEVELS = ["low", "medium", "high"]

# Two sets, every edge bears BOTH ({0 1}) -> Inf(0)&Inf(1) is redundant.
_REDUNDANT_HOA = """HOA: v1
States: 2
Start: 0
AP: 2 "a" "b"
Acceptance: 2 Inf(0)&Inf(1)
--BODY--
State: 0
[0] 1 {0 1}
State: 1
[1] 0 {0 1}
--END--
"""

# Three APs declared, only a,b used -> c is unused.
_UNUSED_AP_HOA = """HOA: v1
States: 1
Start: 0
AP: 3 "a" "b" "c"
Acceptance: 1 Inf(0)
--BODY--
State: 0
[0 | 1] 0 {0}
--END--
"""

def _aps(aut: "spot.twa_graph") -> List[str]:
    return sorted(str(x) for x in aut.ap())

def _desc(aut: "spot.twa_graph") -> str:
    return f"states={aut.num_states()} sets={aut.num_sets()} aps={_aps(aut)} acc={aut.acc()}"

def _case(tag: str, build) -> None:
    print(tag)
    print(f"  before          {_desc(build())}")
    for lvl in _LEVELS:
        a = build()
        clean = spot.postprocess(a, "generic", lvl, "any")
        eq = spot.are_equivalent(a, clean)
        print(f"  generic/{lvl:<6}/any {_desc(clean)}  EQUIV={eq}")
    print()

def main() -> int:
    _case("REDUNDANT acc sets (both on every edge):",
          lambda: spot.automaton(_REDUNDANT_HOA))
    _case("UNUSED AP ('c' declared, never used):",
          lambda: spot.automaton(_UNUSED_AP_HOA))
    _case("STATE reduction (FG(!p|Xq) base):",
          lambda: spot.translate("F G(!p | X q)"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
