#!/usr/bin/env python3
"""
kr/testing/probe_memo_stats.py

Memoization profiler for the reach-formula construction. The >100k
reach_strong guard counts raw CALLS (cache hits included), so it cannot
distinguish "exponential re-expansion" from "heavy fan-in onto a healthy
memo". This probe neutralizes the guard, builds the formula under an alarm,
and reports: raw reach calls, _lru_reach_strong hits/misses/size, wall time,
DAG size. Run the exploding survey cases through it:

    python3 kr/testing/probe_memo_stats.py "(a U b) | Gc"
    python3 kr/testing/probe_memo_stats.py "FGa | FGb" --budget 10
"""

import argparse
import signal
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr import decompose_aut
import aut2ltl.kr.reachability_operators as _ops
from aut2ltl.kr.reachability import _compute_good_muller_sets
from aut2ltl.kr.fin import fin_c


class Budget(Exception):
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("formula")
    ap.add_argument("--budget", type=int, default=10, help="construction alarm (s)")
    args = ap.parse_args()

    f = spot.formula(args.formula)
    casc = decompose_aut(f.translate())
    print(f"cascade: levels={casc.num_levels} sizes={[l.size for l in casc.levels]} "
          f"configs={len(casc.all_configs())} letters={casc.num_letters()}")

    _ops._reach_memo.clear()
    _ops._clear_casc_registry()
    _ops._register_casc(casc)
    _ops._lru_reach_strong.cache_clear()
    if hasattr(_ops, "_helper_memo"):
        _ops._helper_memo.clear()
    # Neutralize the raw-call guard for profiling (it counts hits too).
    _ops.PAPER_REACH_CALLS = -(10 ** 12)

    def on_alarm(sig, frm):
        raise Budget()

    signal.signal(signal.SIGALRM, on_alarm)
    signal.alarm(args.budget)
    # The SIGALRM handler cannot run while the interpreter sits inside one
    # long native call (spot simplify / formula build). The watchdog thread
    # below dumps the Python stack and hard-exits in that case, naming the
    # native call we are stuck in.
    import faulthandler
    faulthandler.dump_traceback_later(args.budget + 3, exit=True)
    t0 = time.monotonic()
    done = "COMPLETE"
    try:
        good_ms = _compute_good_muller_sets(casc)
        print(f"good Muller sets: {len(good_ms)}")
        for c in sorted(set(casc.all_configs())):
            fin_c(c, casc)
    except Budget:
        done = f"ABORTED at {args.budget}s budget"
    finally:
        signal.alarm(0)
    dt = time.monotonic() - t0

    calls = _ops.PAPER_REACH_CALLS + 10 ** 12
    info = _ops._lru_reach_strong.cache_info()
    print(f"status               : {done} ({dt:.2f}s)")
    print(f"reach_strong calls   : {calls}")
    print(f"lru reach            : hits={info.hits} misses={info.misses} "
          f"size={info.currsize} (hit rate "
          f"{100.0 * info.hits / max(info.hits + info.misses, 1):.1f}%)")
    print(f"fin calls            : {_ops.PAPER_FIN_CALLS}")
    if hasattr(_ops, "_helper_memo"):
        print(f"helper memo entries  : {len(_ops._helper_memo)}")


if __name__ == "__main__":
    main()
