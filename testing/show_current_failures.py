#!/usr/bin/env python3
"""
Show current non-equivalent ("no") cases from existing evaluation CSVs.
Sorted by number of states (smallest first).
"""
import csv
from pathlib import Path

CSVS = [
    "current_status_1k.csv",
    "complexity_simple.csv",
    "complexity_medium.csv",
    "complexity_hard.csv",
    "complexity_veryhard.csv",
]

def main():
    all_failures = []

    for csv_name in CSVS:
        csv_path = Path(csv_name)
        if not csv_path.exists():
            continue
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("equivalent") == "no":
                    try:
                        states = int(row.get("states", 99))
                    except ValueError:
                        states = 99
                    all_failures.append({
                        "csv": csv_name,
                        "states": states,
                        "technique": row.get("technique", ""),
                        "original": row.get("original", ""),
                        "recovered": row.get("recovered", ""),
                    })

    # Sort: smallest states first
    all_failures.sort(key=lambda x: (x["states"], x["csv"]))

    print(f"Total non-equivalent cases across all CSVs: {len(all_failures)}\n")
    print("=== Smallest failing formulas (sorted by #states) ===\n")

    for i, f in enumerate(all_failures[:15], 1):
        print(f"{i:2d}. [{f['csv']:<22s}] states={f['states']:2d}  tech={f['technique']}")
        print(f"    orig: {f['original']}")
        print(f"    rec:  {f['recovered']}")
        print()

if __name__ == "__main__":
    main()
