"""Emit the curated survey corpus (`tests/survey_formulas.py`) into the benchmark
input tree as `.ltl` files, one per Manna-Pnueli class, notes preserved as
comments. This is the bench's seed corpus — the same 40 formulas the normal
sweep uses — re-expressed in the file-based `inputs/` format so the bench and the
survey share inputs. Run: `python3 tests/benchmark/from_survey.py`.

Lives outside `inputs/` (which holds raw `.ltl`/`.hoa` only). Re-run to resync.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tests.survey_formulas import SURVEY_CASES  # noqa: E402
from normalize import normalize_ltl  # noqa: E402

# MP-class code -> (filename stem, human title), weakest-first.
_CLASS = {
    "B": ("bottom", "Bottom / trivial"),
    "S": ("safety", "Safety (G-rooted invariants)"),
    "G": ("guarantee", "Guarantee (co-safety, F-reachable)"),
    "O": ("obligation", "Obligation (boolean safety + guarantee)"),
    "R": ("recurrence", "Recurrence (Buchi / Pi_2, infinitely-often)"),
    "P": ("persistence", "Persistence (coBuchi / Sigma_2, eventually-always)"),
    "T": ("reactivity", "Reactivity (full Rabin/Streett)"),
}


def emit(root: str = "tests/benchmark/inputs/core") -> list[str]:
    by_class: dict[str, list] = {}
    for c in SURVEY_CASES:
        by_class.setdefault(c.klass, []).append(c)
    os.makedirs(root, exist_ok=True)
    written: list[str] = []
    for code, (stem, title) in _CLASS.items():
        cases = by_class.get(code, [])
        if not cases:
            continue
        path = os.path.join(root, f"{stem}.ltl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# {title}\n"
                     f"# from tests/survey_formulas.py (the curated survey corpus), "
                     f"AP-renamed to canonical a,b,c… -- resync via "
                     f"tests/benchmark/from_survey.py\n\n")
            for c in cases:
                fh.write(f"{normalize_ltl(c.formula)}  # {c.note}\n")
        written.append(path)
    return written


if __name__ == "__main__":
    for p in emit():
        print(f"wrote {p}")
