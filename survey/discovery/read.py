"""survey.discovery.read — turn a classified file into runnable Example(s).

An HOA file yields one Example; an LTL list yields one Example per non-blank,
non-comment line. Each Example carries provenance (source path / subfolder) so
the CSV records where it came from without any input-order replay.

Bones only — `Example` is the unit the rest of survey consumes.
"""
from __future__ import annotations

# TODO: @dataclass Example: path: Path; kind: Kind; formula: Optional[str]; provenance: str
# TODO: read(path: Path, kind: Kind) -> Iterator[Example]
