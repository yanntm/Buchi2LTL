#!/usr/bin/env python3
"""
tests/kinska_breakdown.py — ventilate a kinska sweep CSV by source subfolder.

kinska.csv records only a row's basename (and a formula string for LTL-list
inputs), and the randltl `*-ba` basenames are NOT unique across the ap folders,
so the folder cannot be read off a row directly. Instead we replay the sweep's
deterministic input order — `find <corpus> -name '*.txt' -not -path '*/logs/*' |
sort`, with each HOA file contributing ONE row and each LTL list one row per
formula line (mirroring survey.py) — and zip it against the CSV rows in order.
HOA rows are cross-checked against the CSV filename; any mismatch aborts (the
order assumption broke). Prints a per-folder verdict tally.

Usage:
    python3 tests/kinska_breakdown.py [kinska.csv] [corpus-root]
"""
import csv
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    ROOT / "tests/samples/kinska/logs/reference/kinska.csv"
CORPUS = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "tests/samples/kinska"

VERDICTS = ("True", "NOT_LTL", "PROBABLY_NOT_LTL", "UNVERIFIED_SIZE", "FALSE")


def _is_hoa(p: Path) -> bool:
    """First non-blank line is `HOA:` — mirrors survey._is_hoa."""
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                return line.lstrip().startswith("HOA:")
    except OSError:
        pass
    return False


def _formula_lines(p: Path) -> List[str]:
    """Non-blank, non-comment lines — mirrors survey._load_inputs."""
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def _expected_rows() -> List[Tuple[str, Optional[str]]]:
    """(folder, hoa_basename_or_None) per CSV row, in sweep input order. Uses the
    exact same `find … | sort` pipeline as kinska_sweep.sh so the locale-aware
    ordering matches the CSV row order byte-for-byte."""
    out = subprocess.run(
        f"find {CORPUS} -type f -name '*.txt' -not -path '*/logs/*' | sort",
        shell=True, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    rows: List[Tuple[str, Optional[str]]] = []
    for f in (Path(x) for x in out):
        folder = str(f.parent.relative_to(CORPUS))
        if _is_hoa(f):
            rows.append((folder, f.name))
        else:
            rows.extend((folder, None) for _ in _formula_lines(f))
    return rows


def main() -> int:
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        data = list(csv.DictReader(fh))
    expected = _expected_rows()
    if len(expected) != len(data):
        print(f"ROW COUNT MISMATCH: corpus replay={len(expected)} csv={len(data)} "
              f"— order assumption broke; aborting.", file=sys.stderr)
        return 1

    tally: dict = defaultdict(Counter)
    for (folder, name), row in zip(expected, data):
        if name is not None and row["formula"] != name:
            print(f"NAME MISMATCH at folder {folder}: expected {name!r} "
                  f"got {row['formula']!r} — aborting.", file=sys.stderr)
            return 1
        tally[folder][row["equiv"]] += 1

    cols = ["True", "NOT_LTL", "FALSE", "BUILD_TIMEOUT", "UNVERIFIED_SIZE", "other"]
    print(f"{'folder':22s} {'cases':>5s} " + " ".join(f"{c:>13s}" for c in cols))
    grand: Counter = Counter()
    for folder in sorted(tally):
        c = tally[folder]
        bto = sum(v for k, v in c.items() if k.startswith("BUILD_TIMEOUT"))
        other = sum(v for k, v in c.items()
                    if k not in ("True", "NOT_LTL", "FALSE", "UNVERIFIED_SIZE")
                    and not k.startswith("BUILD_TIMEOUT"))
        vals = [c["True"], c["NOT_LTL"], c["FALSE"], bto, c["UNVERIFIED_SIZE"], other]
        print(f"{folder:22s} {sum(c.values()):5d} " + " ".join(f"{v:13d}" for v in vals))
        grand.update(c)
    bto = sum(v for k, v in grand.items() if k.startswith("BUILD_TIMEOUT"))
    other = sum(v for k, v in grand.items()
                if k not in ("True", "NOT_LTL", "FALSE", "UNVERIFIED_SIZE")
                and not k.startswith("BUILD_TIMEOUT"))
    vals = [grand["True"], grand["NOT_LTL"], grand["FALSE"], bto,
            grand["UNVERIFIED_SIZE"], other]
    print(f"{'TOTAL':22s} {sum(grand.values()):5d} " + " ".join(f"{v:13d}" for v in vals))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
