"""
genaut/probe_true_collapse.py — of the universal-language ("true") survivors that
the Small pass left non-canonical, how many does spot's STRONGEST reduction
collapse to the 1-state canonical `t`?

Takes the census CSV, selects every row whose reconstructed formula is `1` (the
language is true; all verified equivalent), loads the stored automaton, and runs
spot.postprocess(generic, deterministic, high) on it — the determinizing path the
probe identified as the one that can see universality. Tallies the resulting state
counts and flags any that still do NOT reach the canonical 1-state `t`.

Usage:  python3 genaut/probe_true_collapse.py
"""
from __future__ import annotations

import csv
import os
from collections import Counter
from typing import List

import spot

HERE = os.path.dirname(__file__)
CSV_PATH = os.path.join(HERE, "logs", "genaut.csv")
RAW_DIR = os.path.join(HERE, "raw")

STRONG = ("generic", "deterministic", "high")


def true_files() -> List[str]:
    """Filenames of the survivors aut2ltl reconstructed as `1` (universal)."""
    out: List[str] = []
    with open(CSV_PATH, newline="") as fh:
        for row in csv.DictReader(fh):
            if (row.get("reconstructed") or "").strip() == "1":
                out.append(row["formula"].strip())
    return out


def is_canonical_true(aut: "spot.twa_graph") -> bool:
    """1 state and the acceptance is trivially `t` (accept-all)."""
    return aut.num_states() == 1 and str(aut.get_acceptance()) == "t"


def main() -> None:
    files = true_files()
    print(f"universal ('true') survivors in census: {len(files)}")

    states_hist: Counter = Counter()
    canonical = 0
    holdouts: List[str] = []
    for name in files:
        aut = spot.automaton(os.path.join(RAW_DIR, name))
        r = spot.postprocess(aut, *STRONG)
        states_hist[r.num_states()] += 1
        if is_canonical_true(r):
            canonical += 1
        else:
            holdouts.append(name)

    print(f"after spot.postprocess{STRONG}:")
    print(f"  reached canonical 1-state `t` : {canonical}/{len(files)}")
    print(f"  resulting state-count histogram: "
          f"{dict(sorted(states_hist.items()))}")
    if holdouts:
        print(f"  NOT canonical ({len(holdouts)}), first 10: {holdouts[:10]}")
    else:
        print("  every universal survivor collapsed to the canonical true.")


if __name__ == "__main__":
    main()
