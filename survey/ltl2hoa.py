"""survey.ltl2hoa — fill a peer `hoa/` folder from an `ltl/` folder via ltl2tgba.

Translate every formula in an LTL corpus folder to an ω-automaton (Spot's
`translate`, the `small` recipe — i.e. ltl2tgba) and write one `.hoa` per formula
into a parallel folder, mirroring the source layout. Each output is named for
**traceability**: `<ltl-file-stem>_l<line>.hoa`, where `line` is the formula's
1-based line in its source `.ltl` (so `examples2.ltl` line 17 -> `examples2_l17.hoa`).

Corpus *building*, dataset-agnostic — a sibling of `survey.normalize`.

CLI (from the repo root):
    python3 -m survey.ltl2hoa samples/validation/ltl            # -> samples/validation/hoa
    python3 -m survey.ltl2hoa SRC_LTL_DIR DST_HOA_DIR           # explicit destination
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import spot


def formulas(ltl: Path) -> List[Tuple[int, str]]:
    """The (line-number, formula) pairs of an `.ltl` file — `#` comments and blank
    lines skipped, the 1-based line numbers preserved for traceability."""
    out: List[Tuple[int, str]] = []
    for i, line in enumerate(ltl.read_text(encoding="utf-8").splitlines(), start=1):
        body = line.split("#", 1)[0].strip()
        if body:
            out.append((i, body))
    return out


def build(src: Path, dst: Path) -> int:
    """Translate every formula under `src` into `dst`, mirroring `src`'s layout.
    Returns the number of automata written."""
    n = 0
    for ltl in sorted(src.rglob("*.ltl")):
        rel = ltl.relative_to(src).parent
        for line, f in formulas(ltl):
            aut = spot.translate(f, "small")
            out = dst / rel / f"{ltl.stem}_l{line}.hoa"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(aut.to_str("hoa"), encoding="utf-8")
            n += 1
    return n


def main(argv: List[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    src = Path(argv[0])
    dst = Path(argv[1]) if len(argv) > 1 else src.parent / "hoa"
    n = build(src, dst)
    print(f"ltl2hoa: wrote {n} automata -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
