"""Collect the Kinská HOA automata into the benchmark corpus: flatten her folder
hierarchy into a single `inputs/kinska/`, rename `.txt` -> `.hoa`, and DEDUP by
the normalised key (tests/benchmark/normalize.normalize_hoa) — one representative
per key. Her LTL formula files (`*-formulae/`) are skipped: they are the randltl
SOURCES of the `-ba` automata, redundant with the HOA we keep.

Stores the representative file VERBATIM (only the extension changes) — provenance
preserved; normalisation is only the dedup key, not applied to stored content.
Run: `python3 tests/benchmark/collect_kinska.py`.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import normalize_hoa, _is_hoa_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tests/samples/kinska"
DST = ROOT / "tests/benchmark/inputs/kinska"


def collect() -> None:
    files = sorted(p for p in SRC.rglob("*.txt")
                   if "/logs/" not in p.as_posix() and "-formulae/" not in p.as_posix())
    DST.mkdir(parents=True, exist_ok=True)
    for old in DST.glob("*.hoa"):      # clear stale output (idempotent re-import)
        old.unlink()
    seen: Dict[str, str] = {}          # normalised key -> kept flat name
    kept = dups = skipped = 0
    for p in files:
        text = p.read_text(encoding="utf-8")
        if not _is_hoa_text(text):
            skipped += 1
            continue
        key = normalize_hoa(text)
        if key in seen:
            dups += 1
            continue
        # Flat name encodes her path (her leaf names repeat across ap-folders).
        name = str(p.relative_to(SRC).with_suffix("")).replace("/", "-") + ".hoa"
        seen[key] = name
        shutil.copyfile(p, DST / name)              # flatten + .txt -> .hoa, verbatim
        kept += 1
    print(f"{len(files)} .txt files: {kept} kept (unique HOA), "
          f"{dups} dropped as dups, {skipped} non-HOA skipped")


if __name__ == "__main__":
    collect()
