"""survey.discovery — find the examples survey can run under the given paths.

Orchestrates the three small concerns below into one `discover(paths)`:

    walk    recurse PATHs (file or folder) → candidate files
    detect  classify a candidate by content → HOA / LTL list / skip
    read    turn a classified file into runnable Example(s) (+ provenance)

Bones only.
"""
from __future__ import annotations

# TODO: discover(paths: Iterable[Path]) -> Iterator[Example]   (walk → detect → read)
