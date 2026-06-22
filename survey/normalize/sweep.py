"""survey.normalize.sweep — the shared folder harness for the in-place corpus
tools (`dedup`, `canon`).

Walk a folder's `.ltl`/`.hoa` files recursively in sorted path order, hand each
to an `Op`, and either REPORT what would change (dry run) or APPLY it (`--prune`).
Each tool supplies only its per-file `Op`; the walk, the dry-run/apply switch and
the tally live here, once — so `dedup` and `canon` share one API.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

SUFFIXES = {".ltl", ".hoa"}

# An Op inspects one file's (path, text) and returns (new_text, n):
#   new_text is None -> leave the file unchanged
#   new_text == ""   -> delete the file
#   new_text is str  -> rewrite the file with this content
# n counts the items (dropped lines, renamed/deleted files) to tally in the report.
Op = Callable[[Path, str], Tuple[Optional[str], int]]


def files(folder: Path) -> List[Path]:
    """Every `.ltl`/`.hoa` file under `folder`, recursively, in sorted order."""
    return sorted(p for p in folder.rglob("*")
                  if p.is_file() and p.suffix in SUFFIXES)


def run(folder: Path, op: Op, *, apply: bool) -> Tuple[Dict[Path, int], List[Path]]:
    """Apply `op` to every file. Returns (changed, removed): per-file change counts
    and the files that were (or, in a dry run, would be) deleted. Writes only when
    `apply` is true."""
    changed: Dict[Path, int] = {}
    removed: List[Path] = []
    for p in files(folder):
        new, n = op(p, p.read_text(encoding="utf-8"))
        if new is None or n == 0:
            continue
        changed[p] = n
        if new == "":
            removed.append(p)
            if apply:
                p.unlink()
        elif apply:
            p.write_text(new, encoding="utf-8")
    return changed, removed


def cli(op: Op, argv: Sequence[str], *, verb: str) -> int:
    """Shared `[--prune] FOLDER` entry: dry run by default, apply with `--prune`.
    `verb` is the action word for the report (e.g. 'drop', 'normalize')."""
    rest = [a for a in argv if a != "--prune"]
    apply = "--prune" in argv
    if not rest:
        print(__doc__)
        return 2
    folder = Path(rest[0])
    changed, removed = run(folder, op, apply=apply)
    for p in sorted(changed):
        print(f"{p.relative_to(folder)}: {changed[p]}")
    n = sum(changed.values())
    tail = f", {len(removed)} files deleted" if removed else ""
    state = "[applied]" if apply else "[dry run -- pass --prune to apply]"
    print(f"{verb}: {n} items in {len(changed)} files{tail}  {state}")
    return 0
