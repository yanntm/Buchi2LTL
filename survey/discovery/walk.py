"""survey.discovery.walk — recurse the given PATHs into candidate files.

A PATH may be a file (yielded as-is) or a folder (descended recursively).
Hidden dirs and `logs/` are skipped. Pure filesystem — no format knowledge.

Bones only.
"""
from __future__ import annotations

# TODO: walk(paths: Iterable[Path]) -> Iterator[Path]
