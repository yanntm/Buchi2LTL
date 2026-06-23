"""survey.example — the unit of input the rest of survey consumes.

An Example is one thing to reconstruct: an inline LTL formula, or an HOA
automaton file. `value` is what gets handed to the front end (the formula text,
or the file path); `display` is what the CSV's input column shows; `source`
records provenance (the originating folder file, or "--ltl"/"--hoa").
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Example:
    kind: str            # "ltl" | "hoa"
    value: str           # formula text (ltl) or HOA file path (hoa)
    display: str         # the input column in the CSV / trace
    source: str = ""     # unique provenance key, emitted as the CSV `source` column
                         # (relative path | file:line | --ltl:k)

    @property
    def is_hoa(self) -> bool:
        return self.kind == "hoa"
