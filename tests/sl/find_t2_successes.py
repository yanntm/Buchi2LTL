#!/usr/bin/env python3
"""
Search for LTL formulas where the *current production* terminal-2-SCC
heuristic (t2, including entry-timing logic and validation) activates
inside reconstruct_ltl and produces a language-equivalent result.

This is the modern equivalent of how f2_successes.py was generated.

We use randltl + the integrated reconstruct_ltl (which tries f2 then t2).
We collect formulas where "t2" appears in the technique and the round-trip
is equivalent according to Spot.

Hard timeout, target 100.
"""

import sys
import time
from pathlib import Path

import spot

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from aut2ltl.sl import reconstruct_ltl

TIME_LIMIT = 300.0     # 5 minutes - increase if needed
TARGET = 100
BATCH_SIZE = 120

# Sweeps a bit wider than the random test to find more t2 cases
PARAM_SWEEP = [
    (2, 5), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10), (2, 11),
    (3, 5), (3, 6), (3, 7), (3, 8), (3, 9), (3, 10), (3, 11), (3, 12),
    (4, 5), (4, 6), (4, 7), (4, 8), (4, 9), (4, 10),
]

def main():
    start = time.time()
    successes = []
    seen = set()
    pidx = 0

    print("=== Searching for formulas where modern production t2 triggers ===")
    print(f"Target: {TARGET} formulas where 't2' appears in technique + equivalent")
    print(f"Timeout: {TIME_LIMIT}s")
    print("Using current reconstruct_ltl (with entry-timing + validation)")
    print()

    while time.time() - start < TIME_LIMIT and len(successes) < TARGET:
        if pidx >= len(PARAM_SWEEP):
            pidx = 0
        aps, tree_size = PARAM_SWEEP[pidx]
        pidx += 1

        try:
            gen = spot.randltl(aps, n=BATCH_SIZE, seed=int(time.time()*1000) % 100000,
                               tree_size=tree_size, simplify=1, output="ltl")
            for f in gen:
                if len(successes) >= TARGET:
                    break
                orig_str = str(f)
                if orig_str in seen:
                    continue
                seen.add(orig_str)

                try:
                    aut = f.translate("GeneralizedBuchi", "Small", "High")
                    if aut.num_states() > 20:
                        continue

                    rec, _, tech = reconstruct_ltl(aut)
                    if "t2" not in tech:
                        continue
                    if rec.startswith("UNSUPPORTED"):
                        continue

                    orig_formula = spot.formula(orig_str)
                    rec_formula = spot.formula(rec)
                    if spot.are_equivalent(orig_formula, rec_formula):
                        successes.append({
                            "formula": orig_str,
                            "aps": aps,
                            "tree_size": tree_size,
                            "states": aut.num_states(),
                            "technique": tech,
                        })
                        print(f"  [{len(successes):3d}] {orig_str[:80]}  (states={aut.num_states()}, tech={tech})")
                except Exception:
                    pass
        except Exception:
            pass

        if len(successes) % 10 == 0 and successes:
            print(f"  ... {len(successes)} found so far, elapsed {time.time()-start:.1f}s")

    total_time = time.time() - start
    print(f"\nSearch finished after {total_time:.1f}s. Found {len(successes)} formulas.")

    if successes:
        out_path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "t2_successes.py"
        with open(out_path, "w") as f:
            f.write('"""Formulas for which the modern production terminal-2-SCC\n')
            f.write('heuristic (t2) activated inside reconstruct_ltl and produced\n')
            f.write('a language-equivalent result.\n')
            f.write('Includes the entry-timing logic (synchronous vs delayed attachment)\n')
            f.write('and full validation round-trips.\n')
            f.write(f'\nSearch time: {total_time:.1f}s, target={TARGET}\n')
            f.write('Generated with testing/find_t2_successes.py\n"""\n\n')
            f.write("T2_SUCCESS = [\n")
            for s in successes:
                f.write(f'    "{s["formula"]}",\n')
            f.write("]\n\n")
            f.write("# Metadata\n")
            f.write("T2_SUCCESS_META = [\n")
            for s in successes:
                f.write(f'    {{"formula": "{s["formula"]}", "aps": {s["aps"]}, '
                        f'"tree_size": {s["tree_size"]}, "states": {s["states"]}, '
                        f'"technique": "{s["technique"]}"}},\n')
            f.write("]\n")

        print(f"Saved to {out_path}")
    else:
        print("No successes found in time. Try increasing TIME_LIMIT or broadening the sweep.")

if __name__ == "__main__":
    main()
