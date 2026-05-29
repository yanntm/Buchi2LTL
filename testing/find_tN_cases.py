#!/usr/bin/env python3
"""
Search for LTL formulas where the *generalized* terminal-SCC heuristic (tN)
captures SCCs of size >=3 (producing technique tags "t3", "t4", ...).

We generate random formulas (with emphasis on 3-6 APs as suggested) PLUS
synthetic "phased" cores using disjoint label partitions (easy with more APs).

We throw them at reconstruct_ltl and watch the returned technique string.

Hits are formulas where the technique contains "t3" or higher AND the
round-trip is language-equivalent.

We also log "near-misses": formulas where the cheap syntactic detector
(find_nice_terminal_2sccs) sees a size>=3 nice terminal SCC (the relaxed rule
fired), even if the soundness validation gate later rejected the fragment.

Hard timeout. Target 100 (ambitious; expect far fewer full t3+ hits).

Usage:
    python3 testing/find_tN_cases.py
"""
import sys
import time
from pathlib import Path
import itertools

import spot

sys.path.insert(0, str(Path(__file__).parent.parent))
from buchi2ltl.heuristics.terminal_2scc import (
    find_nice_terminal_2sccs,
    try_terminal_2scc_with_validation,
)
from buchi2ltl.reconstruction import reconstruct_ltl

TIME_LIMIT = 300.0      # 5 minutes hard timeout (user request)
TARGET = 100
BATCH_SIZE = 80

# Higher AP counts + varied complexity (more APs make disjoint partitions easy)
PARAM_SWEEP = [
    (3, 6), (3, 7), (3, 8), (3, 9), (3, 10), (3, 12), (3, 14),
    (4, 5), (4, 6), (4, 7), (4, 8), (4, 9), (4, 10), (4, 12), (4, 14),
    (5, 6), (5, 7), (5, 8), (5, 9), (5, 10),
    (6, 5), (6, 6), (6, 7), (6, 8),
]


def make_phased_core(k: int, m: int):
    """Return (core_formula_str, Li_list) for a k-phase G with disjoint Li
    using m props (minterms). k <= 2**m.
    """
    if k > (1 << m):
        return None, None
    props = [f"p{i}" for i in range(m)]
    # First k minterms in lex order
    minterms = []
    for bits in itertools.product([0, 1], repeat=m):
        if len(minterms) >= k:
            break
        lit = " & ".join(
            ("" if b else "!") + props[j] for j, b in enumerate(bits)
        )
        minterms.append(lit)
    if len(minterms) < k:
        return None, None
    Li = minterms[:k]
    terms = []
    for i in range(k):
        cur = Li[i]
        nxt = Li[(i + 1) % k]
        terms.append(f"({cur} & X({nxt}))")
    core = "G( " + " | ".join(terms) + " )"
    return core, Li


def generate_synthetics(max_k=5, variants_per_k=8):
    """Yield a bunch of synthetic formulas likely to have nice >=3 terminal SCCs."""
    for k in range(3, max_k + 1):
        for m in range(2, 5):
            core, Li = make_phased_core(k, m)
            if not core:
                continue
            # Base core (safety)
            yield core
            # Light wrappers that often preserve a terminal nice SCC
            yield f"({core}) & G(true)"
            yield f"FG({core})"           # liveness wrapper (may cause acc mismatch)
            yield f"GF(p0 & X({core}))"
            yield f"p{k} U ({core})"
            # Extra don't-care props (helps some translations)
            if m < 4:
                extra = f"p{m}"
                yield f"({extra} | ({core}))"
                yield f"G({extra} | ({core}))"
            # A few more mutations
            for v in range(variants_per_k):
                # Different outer operators with extra props
                p_extra = f"p{(k + v) % 5}"
                yield f"({p_extra} -> {core})"
                yield f"X({core})"
                yield f"F({core})"


def has_tN(technique: str, min_n: int = 3) -> bool:
    """Return True if technique contains t3, t4, ... (or higher than min_n)."""
    import re
    for m in re.finditer(r"t(\d+)", technique):
        if int(m.group(1)) >= min_n:
            return True
    return False


def main():
    start = time.time()
    full_hits = []          # technique showed t3+
    near_misses = []        # cheap detector saw size>=3 (even if validate failed)
    seen = set()
    pidx = 0
    synth_gen = generate_synthetics()
    synth_count = 0

    print("=== Searching for generalized tN (size>=3) terminal-SCC captures ===")
    print(f"Target: {TARGET} full hits (t3+ in technique + equiv)")
    print(f"Hard timeout: {TIME_LIMIT}s")
    print("Strategy: high-AP randltl + synthetic phased cores (more APs help partitions)")
    print("We report BOTH full technique hits AND near-misses (nice detector size>=3).")
    print()

    while (time.time() - start) < TIME_LIMIT and len(full_hits) < TARGET:
        # Alternate between random batches and synthetics
        use_synth = (len(full_hits) + len(near_misses)) % 3 == 0 and synth_count < 2000

        formulas_this_round = []
        if use_synth:
            try:
                for _ in range(20):
                    fstr = next(synth_gen)
                    formulas_this_round.append(("synth", fstr))
                    synth_count += 1
            except StopIteration:
                pass
        else:
            if pidx >= len(PARAM_SWEEP):
                pidx = 0
            aps, tree_size = PARAM_SWEEP[pidx]
            pidx += 1
            try:
                gen = spot.randltl(
                    aps, n=BATCH_SIZE,
                    seed=int(time.time() * 1000) % 1000000,
                    tree_size=tree_size, simplify=1, output="ltl"
                )
                for f in gen:
                    formulas_this_round.append(("rand", str(f)))
            except Exception:
                pass

        for src, orig_str in formulas_this_round:
            if (time.time() - start) >= TIME_LIMIT:
                break
            if orig_str in seen:
                continue
            seen.add(orig_str)

            try:
                aut = spot.formula(orig_str).translate(
                    "GeneralizedBuchi", "Small", "High"
                )
                if aut.num_states() > 25:
                    continue

                # 1. Cheap syntactic detector (the relaxed rule itself)
                nice_all = find_nice_terminal_2sccs(aut)
                big_nice = [n for n in nice_all if len(n["states"]) >= 3]
                if big_nice:
                    max_big = max(len(n["states"]) for n in big_nice)
                    print(f"  [NEAR] size>={max_big} nice SCC(s) detected (source={src}): {orig_str[:75]}")
                    near_misses.append({
                        "formula": orig_str,
                        "source": src,
                        "states": aut.num_states(),
                        "max_nice_size": max_big,
                        "num_big": len(big_nice),
                        "example_L": big_nice[0]["L"],
                    })
                    # keep only a reasonable number of near-misses
                    if len(near_misses) > 200:
                        near_misses.pop(0)

                # 2. Full validating path + reconstruct (what actually sets the technique tag)
                rec, _, tech = reconstruct_ltl(aut)
                if has_tN(tech, 3):
                    if rec.startswith("UNSUPPORTED"):
                        continue
                    orig_f = spot.formula(orig_str)
                    rec_f = spot.formula(rec)
                    if spot.are_equivalent(orig_f, rec_f):
                        full_hits.append({
                            "formula": orig_str,
                            "source": src,
                            "aps": aut.ap().size() if hasattr(aut, "ap") else "?",
                            "states": aut.num_states(),
                            "technique": tech,
                        })
                        print(f"  [HIT #{len(full_hits)}] {tech}: {orig_str[:70]}")
                        if len(full_hits) >= TARGET:
                            break
            except Exception:
                continue

        if (len(full_hits) + len(near_misses)) % 20 == 0 and (full_hits or near_misses):
            elapsed = time.time() - start
            print(f"  ... progress: {len(full_hits)} full t3+ hits, {len(near_misses)} near-misses, "
                  f"elapsed {elapsed:.1f}s")

    total = time.time() - start
    print(f"\n=== Search finished after {total:.1f}s ===")
    print(f"Full t3+ hits (technique contains t3/t4/... + equiv): {len(full_hits)}")
    print(f"Near-misses (relaxed nice-detector saw size>=3 SCC):   {len(near_misses)}")

    out_dir = Path(__file__).parent.parent / "samples"
    out_path = out_dir / "tN_successes.py"

    with open(out_path, "w") as f:
        f.write('"""Formulas where the generalized terminal-SCC heuristic (tN)\n')
        f.write('produced a technique tag t3 or higher (i.e. captured a nice\n')
        f.write('terminal SCC of size >=3) and the full reconstruction was\n')
        f.write('language-equivalent.\n')
        f.write(f'\nSearch time: {total:.1f}s (timeout={TIME_LIMIT}), target={TARGET}\n')
        f.write('Generated with testing/find_tN_cases.py\n"""\n\n')

        f.write("TN_SUCCESS = [\n")
        for h in full_hits:
            f.write(f'    "{h["formula"]}",\n')
        f.write("]\n\n")

        f.write("# Metadata for the full hits\n")
        f.write("TN_SUCCESS_META = [\n")
        for h in full_hits:
            f.write(f'    {{"formula": "{h["formula"]}", "source": "{h["source"]}", '
                    f'"states": {h["states"]}, "technique": "{h["technique"]}"}},\n')
        f.write("]\n\n")

        f.write("# Near-misses: the cheap (relaxed) detector saw size>=3 nice SCCs\n")
        f.write("# even if validation or full reconstruct did not ultimately use them.\n")
        f.write("TN_NEAR_MISSES = [\n")
        for n in near_misses[:50]:   # limit file size
            f.write(f'    {{"formula": "{n["formula"]}", "source": "{n["source"]}", '
                    f'"states": {n["states"]}, "max_nice_size": {n["max_nice_size"]}, '
                    f'"example_L": {n["example_L"]}}},\n')
        f.write("]\n")

    print(f"\nSaved results (full hits + sample of near-misses) to {out_path}")

    if full_hits:
        print("\nExample full hits:")
        for h in full_hits[:5]:
            print(f"  tech={h['technique']}: {h['formula'][:80]}")
    else:
        print("\nNo full t3+ technique hits in this run (the combination of nice large SCC + "
              "validation passing for the emitted G-N fragment is rare).")
        print("The near-miss list contains concrete formulas where the *relaxed size>=3 rule* "
              "fired in the cheap detector.")

    if near_misses:
        print(f"\nSample near-miss (relaxed rule saw large SCC):")
        nm = near_misses[0]
        print(f"  size={nm['max_nice_size']}  {nm['formula'][:90]}")
        print(f"  L labels: {nm['example_L']}")


if __name__ == "__main__":
    main()
