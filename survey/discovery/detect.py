"""survey.discovery.detect — classify a candidate file by content.

Answers only "can survey read this, and as what?": HOA automaton (by header /
content), LTL list (one formula per non-blank, non-comment line), or skip. No
technique knowledge here.

Bones only.
"""
from __future__ import annotations

# TODO: Kind = Literal["hoa", "ltl"]   (None ⇒ skip)
# TODO: detect(path: Path) -> Optional[Kind]
