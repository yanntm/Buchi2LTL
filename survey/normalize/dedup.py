"""Dedup a folder of inputs by a pluggable `key`: walk it in sorted path order,
keep the first item per key, treat the rest as duplicates. This module knows
folder navigation and the keep/drop decision only — not WHAT the key means (that
is the caller's callable, by default `names` then `polarity`).

A file contributes one item if it is HOA, one per non-comment formula line if it
is LTL. By default it only REPORTS (dry run, nothing written); `--prune` is the
explicit opt-in that deletes duplicate HOA files and removes duplicate formula
lines from LTL files.

CLI:
    python3 .../dedup.py FOLDER            # dry run: per-file drop counts, no writes
    python3 .../dedup.py --prune FOLDER    # apply: delete / rewrite the duplicates
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from names import _is_hoa_text, normalize_text         # noqa: E402
from polarity import polarity_normalize_text            # noqa: E402

Key = Callable[[str], str]
_SUFFIXES = {".ltl", ".hoa"}


def default_key(text: str) -> str:
    """The combined key: name canonicalisation then polarity canonicalisation."""
    return polarity_normalize_text(normalize_text(text))


def scan(folder: Path, key: Key, apply: bool) -> Tuple[Dict[Path, int], List[Path], int]:
    """Walk `folder` in sorted path order, keep the first item per key. Returns
    (dropped-LTL-count per file, dropped-HOA files, total items). When `apply`,
    delete duplicate HOA files and rewrite LTL files without their duplicate lines."""
    seen: set[str] = set()
    dropped_ltl: Dict[Path, int] = {}
    dropped_hoa: List[Path] = []
    total = 0
    for p in sorted(folder.rglob("*")):
        if not p.is_file() or p.suffix not in _SUFFIXES:
            continue
        text = p.read_text(encoding="utf-8")
        if _is_hoa_text(text):
            total += 1
            k = key(text)
            if k in seen:
                dropped_hoa.append(p)
                if apply:
                    p.unlink()
            else:
                seen.add(k)
            continue
        kept: List[str] = []
        n_drop = 0
        for line in text.splitlines():
            body = line.split("#", 1)[0].strip()
            if body:
                total += 1
                k = key(body)
                if k in seen:
                    n_drop += 1
                    continue
                seen.add(k)
            kept.append(line)
        if n_drop:
            dropped_ltl[p] = n_drop
            if apply:
                p.write_text("\n".join(kept) + ("\n" if text.endswith("\n") else ""),
                             encoding="utf-8")
    return dropped_ltl, dropped_hoa, total


def _emit(folder: Path, dropped_ltl: Dict[Path, int], dropped_hoa: List[Path],
          total: int, verb: str) -> int:
    for p in sorted(dropped_ltl):
        print(f"{p.relative_to(folder)}: {dropped_ltl[p]}")
    for p in dropped_hoa:
        print(p.relative_to(folder))
    n = sum(dropped_ltl.values()) + len(dropped_hoa)
    print(f"{verb} {n} of {total} items, {total - n} survive")
    return n


def dry_run(folder: Path, key: Key = default_key) -> None:
    n = _emit(folder, *scan(folder, key, apply=False), verb="would drop")
    if n:
        print("# dry run, nothing modified -- pass --prune to apply")


def prune(folder: Path, key: Key = default_key) -> None:
    _emit(folder, *scan(folder, key, apply=True), verb="dropped")


if __name__ == "__main__":
    args = sys.argv[1:]
    do_prune = "--prune" in args
    paths = [a for a in args if a != "--prune"]
    if not paths:
        print(__doc__)
        raise SystemExit(2)
    (prune if do_prune else dry_run)(Path(paths[0]))
