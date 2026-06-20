"""survey.inputs — discover the examples survey can run, under the given paths.

Walks each PATH (file or folder) recursively and yields the runnable examples:
HOA automata (detected by content) and LTL formulas (one per line in a `.ltl`
file). Unreadable / unrecognized files are skipped, never fatal. Each yielded
example records enough provenance (source path / subfolder) for the CSV, so no
input-order replay is ever needed downstream.

Bones only — logic to migrate from tests/survey.py's input routing.
"""
from __future__ import annotations

# TODO: Example dataclass (path, kind: 'hoa'|'ltl', formula, provenance)
# TODO: discover(paths: Iterable[Path]) -> Iterator[Example]
