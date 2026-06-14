#!/usr/bin/env python3
"""
BuchiToLTL round-trip evaluation harness.

Supports two modes:
- Random formulas via Spot's randltl (the original behavior)
- Stable / curated formulas loaded from files (Python modules or plain text)

The script always runs explicit formulas first (when provided via --samples or --formulas),
then generates additional random formulas (unless --no-random is used).

Usage examples:
    # Stable set only (samples + any extra files)
    python3 evaluate.py --samples --no-random -o samples_results.csv

    # Samples + 200 randoms
    python3 evaluate.py --samples -n 200 --seed 42 -o mixed.csv

    # Load custom formula files (Python lists or one-per-line text)
    python3 evaluate.py -f my_formulas.py -f extra.txt --no-random -o custom.csv

    # Original random-only usage still works
    python3 evaluate.py -n 100 --seed 42 --aps 3 --tree-size 10 -o results.csv
"""

import argparse
import csv
import time
from datetime import datetime

import importlib.util
import os
import spot

from buchi2ltl.reconstruction import reconstruct_ltl


def load_formulas_from_python(path):
    """Load formulas from a Python file by collecting all string items from uppercase list/tuple variables."""
    spec = importlib.util.spec_from_file_location("_formulas_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    formulas = []
    for name in dir(mod):
        if name.startswith("_"):
            continue
        val = getattr(mod, name)
        if isinstance(val, (list, tuple)):
            for item in val:
                if isinstance(item, str) and item.strip():
                    formulas.append(item.strip())

    # Deduplicate while preserving order
    seen = set()
    out = []
    for f in formulas:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def load_formulas_from_text(path):
    """Load one formula per line from a plain text file (ignores blank lines and # comments)."""
    formulas = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                formulas.append(line)
    return formulas


def load_formulas(paths):
    """Load and deduplicate formulas from a list of files (mix of .py and text)."""
    all_formulas = []
    for p in paths:
        if not os.path.exists(p):
            print(f"Warning: formula file not found: {p}")
            continue
        if p.endswith(".py"):
            all_formulas.extend(load_formulas_from_python(p))
        else:
            all_formulas.extend(load_formulas_from_text(p))

    # Global dedup preserving order
    seen = set()
    out = []
    for f in all_formulas:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def main():
    parser = argparse.ArgumentParser(
        description="LTL → TGBA → reconstructed LTL round-trip tester (supports stable formula sets + random generation)"
    )
    parser.add_argument("-n", "--count", type=int, default=100,
                        help="Number of additional random formulas to test after any explicit ones")
    parser.add_argument("--aps", type=int, default=3,
                        help="Number of atomic propositions for randltl")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed for reproducibility of the random part")
    parser.add_argument("--tree-size", type=int, default=10,
                        help="Tree size passed to randltl (lower = simpler formulas)")
    parser.add_argument("--simplify", type=int, default=2,
                        help="randltl simplification level (0-3)")
    parser.add_argument("-o", "--output", type=str, default="results.csv",
                        help="Output CSV file path")
    parser.add_argument("--only-failures", action="store_true",
                        help="Only record formulas where equivalence failed or an error occurred")
    parser.add_argument("--progress", type=int, default=20,
                        help="Print a progress line every N formulas")
    parser.add_argument("--max-states", type=int, default=20,
                        help="Skip formulas whose TGBA has more than this many states (safety)")

    # New stable input support
    parser.add_argument("-f", "--formulas", action="append", default=[],
                        metavar="FILE",
                        help="Load formulas from FILE (Python module with lists of strings, or plain text one-per-line). Can be repeated.")
    parser.add_argument("--samples", action="store_true",
                        help="Include the curated formulas from samples/formulas.py (stable regression set)")
    parser.add_argument("--no-random", action="store_true",
                        help="Skip the random formula generation phase (only run explicit formulas from --samples/--formulas)")

    args = parser.parse_args()

    # === Collect explicit formulas (stable set) ===
    explicit_formulas = []
    sources_for_explicit = {}  # formula -> source label

    if args.samples:
        samples_path = os.path.join(os.path.dirname(__file__), "samples", "formulas.py")
        if not os.path.exists(samples_path):
            samples_path = "samples/formulas.py"
        loaded = load_formulas([samples_path])
        for f in loaded:
            if f not in sources_for_explicit:
                sources_for_explicit[f] = "samples/formulas.py"
        explicit_formulas.extend(loaded)

    if args.formulas:
        loaded = load_formulas(args.formulas)
        for f in loaded:
            if f not in sources_for_explicit:
                src_label = "file:" + os.path.basename(args.formulas[0]) if len(args.formulas) == 1 else "file:multiple"
                sources_for_explicit[f] = src_label
        explicit_formulas.extend(loaded)

    # Dedup explicit while preserving order
    seen = set()
    deduped_explicit = []
    for f in explicit_formulas:
        if f not in seen:
            seen.add(f)
            deduped_explicit.append(f)
    explicit_formulas = deduped_explicit

    num_explicit = len(explicit_formulas)
    do_random = (not args.no_random) and (args.count > 0)
    total_planned = num_explicit + (args.count if do_random else 0)

    print("=== BuchiToLTL Round-Trip Evaluation ===")
    print(f"Explicit formulas : {num_explicit}  (from --samples/--formulas)")
    if do_random:
        print(f"Random formulas   : {args.count}")
    else:
        print("Random formulas   : 0  (--no-random or --count=0)")
    print(f"Total planned     : {total_planned}")
    print(f"APs (for random)  : {args.aps}")
    print(f"Seed (for random) : {args.seed}")
    print(f"Tree size         : {args.tree_size}")
    print(f"Max states        : {args.max_states}")
    print(f"Output            : {args.output}")
    print(f"Start time        : {datetime.now().isoformat(timespec='seconds')}")
    print()

    fieldnames = [
        "id", "seed", "aps", "tree_size", "original", "recovered",
        "equivalent", "states", "acceptance", "time_ms", "technique", "error",
        "source"
    ]

    with open(args.output, "w", newline="", encoding="utf-8") as outf:
        writer = csv.DictWriter(outf, fieldnames=fieldnames,
                                quoting=csv.QUOTE_ALL, escapechar="\\")
        writer.writeheader()

        start = time.time()
        failures = 0
        errors = 0
        skipped = 0
        current_id = 1

        def process_one(original, source_label):
            """Process a single formula (from file or random) and write a row."""
            nonlocal failures, errors, skipped, current_id
            row = {
                "id": current_id,
                "seed": args.seed if source_label.startswith("random") else "",
                "aps": args.aps if source_label.startswith("random") else "",
                "tree_size": args.tree_size if source_label.startswith("random") else "",
                "original": original,
                "recovered": "",
                "equivalent": "",
                "states": "",
                "acceptance": "",
                "time_ms": "",
                "technique": "",
                "error": "",
                "source": source_label,
            }

            t0 = time.time()
            try:
                f = spot.formula(original)
                aut = f.translate("GeneralizedBuchi", "Small", "High")
                states = aut.num_states()
                row["states"] = states
                row["acceptance"] = str(aut.get_acceptance())

                if states > args.max_states:
                    skipped += 1
                    row["error"] = f"too_many_states:{states}"
                    row["equivalent"] = "skipped"
                else:
                    res = reconstruct_ltl(aut)
                    recovered = res.formula      # spot.formula or UNSUPPORTED str
                    technique = res.technique_str()
                    row["recovered"] = str(recovered)
                    row["technique"] = technique

                    if isinstance(recovered, str) and recovered.startswith("UNSUPPORTED"):
                        # Expected limitation — record cleanly instead of crashing later
                        row["equivalent"] = "unsupported"
                        failures += 1
                    else:
                        rec_f = recovered if isinstance(recovered, spot.formula) else spot.formula(str(recovered))
                        eq = spot.are_equivalent(f, rec_f)
                        row["equivalent"] = "yes" if eq else "no"
                        if not eq:
                            failures += 1

            except Exception as e:
                errors += 1
                failures += 1
                row["error"] = str(e)[:300]
                row["equivalent"] = "error"

            row["time_ms"] = int((time.time() - t0) * 1000)

            if not args.only_failures or row["equivalent"] not in ("yes", "skipped"):
                writer.writerow(row)

            current_id += 1

        # === Phase 1: explicit / stable formulas ===
        for orig in explicit_formulas:
            source = sources_for_explicit.get(orig, "explicit")
            process_one(orig, source)

        if num_explicit > 0:
            elapsed = time.time() - start
            print(f"[explicit {num_explicit}/{num_explicit}]  done in {elapsed:.2f}s")
        elif do_random:
            # no explicit phase, progress will come from random loop
            pass

        # === Phase 2: random formulas (if requested) ===
        if do_random:
            gen = spot.randltl(
                args.aps,
                n=args.count,
                seed=args.seed,
                tree_size=args.tree_size,
                simplify=args.simplify,
                output="ltl"
            )

            for i, f in enumerate(gen, 1):
                original = str(f)
                source = f"random(seed={args.seed})"
                process_one(original, source)

                done = num_explicit + i
                if (done % args.progress == 0) or (i == args.count):
                    elapsed = time.time() - start
                    rate = done / elapsed if elapsed > 0 else 0
                    print(f"[{done:4d}/{total_planned}]  "
                          f"fail={failures:3d}  err={errors:2d}  skip={skipped:2d}  "
                          f"{rate:5.1f}/s  {elapsed:6.1f}s")

    total = time.time() - start
    tested_random = args.count if do_random else 0
    total_tested = num_explicit + tested_random
    success = total_tested - failures
    print()
    print("=== Final Summary ===")
    print(f"Explicit formulas : {num_explicit}")
    print(f"Random formulas   : {tested_random}")
    print(f"Total tested      : {total_tested}")
    print(f"Equivalence OK    : {success}")
    print(f"Failures          : {failures}")
    print(f"  - real errors   : {errors}")
    print(f"  - skipped       : {skipped}")
    if total_tested > 0:
        print(f"Success rate      : {success / total_tested * 100:.1f}%")
    print(f"Total time        : {total:.2f}s")
    print(f"CSV written to    : {args.output}")


if __name__ == "__main__":
    main()
