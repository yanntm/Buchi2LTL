"""Emit one HOA automaton per formula line of a fixtures .ltl list.

Mirrors the fixtures convention (samples/fixtures/README.md): for each source
list `ltl/<set>/<stem>.ltl`, write `hoa/<set>/<stem>_l<lineno>.hoa` — one
automaton per non-comment line, via `spot.translate` (ltl2tgba over the list).
Line numbers are 1-indexed against the source so a name pins its exact source
line. Re-runnable: overwrites in place. Run from the repo root.

    python3 -m tests.smoke.gen_hoa            # default: every ltl/sere/*.ltl
    python3 -m tests.smoke.gen_hoa DIR SRC... # a hoa/ out dir + one or more .ltl
"""
import sys
import pathlib
from typing import List

import spot

DEFAULT_OUT = "samples/fixtures/hoa/sere"
DEFAULT_SRC_DIR = "samples/fixtures/ltl/sere"


def emit(out_dir: str, sources: List[str]) -> int:
    """Translate every non-comment line of each source into `out_dir`, named
    `<sourcestem>_l<lineno>.hoa`. Returns the count written."""
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for src in sources:
        stem = pathlib.Path(src).stem
        for lineno, raw in enumerate(pathlib.Path(src).read_text().splitlines(), 1):
            formula = raw.split("#", 1)[0].strip()   # drop inline / whole-line comments
            if not formula:
                continue
            aut = spot.translate(spot.formula(formula))
            aut.save(str(out / f"{stem}_l{lineno}.hoa"))
            n += 1
    return n


def main(argv: List[str]) -> int:
    if argv:
        out_dir = argv[0]
        sources = argv[1:] or sorted(str(p) for p in pathlib.Path(DEFAULT_SRC_DIR).glob("*.ltl"))
    else:
        out_dir = DEFAULT_OUT
        sources = sorted(str(p) for p in pathlib.Path(DEFAULT_SRC_DIR).glob("*.ltl"))
    n = emit(out_dir, sources)
    print(f"wrote {n} automata into {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
