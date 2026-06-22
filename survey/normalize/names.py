"""Normalise the names of the atomic propositions of an LTL formula or of a HOA
automaton: rename them to a, b, c, … in order of first occurrence, and NOTHING
else (no simplification, no reordering, no minimisation).

Two inputs that differ only by AP names map to the same string, so an exact-text
compare of normalised forms is a sound, conservative syntactic key.

- LTL  : token-level rename over the formula string (lowercase-initial tokens,
  minus the `true`/`false` constants; operators are uppercase / symbolic and are
  never touched).
- HOA  : rewrite the quoted names on the `AP:` preamble line to canonical names in
  index order. Transitions reference APs by index, so this is purely cosmetic — a
  weak key: it collapses name-variants and exact-duplicate automata, but NOT
  automata equal up to state renumbering / transition reordering.

CLI:
    python3 .../names.py '<formula>'        # print normalised LTL
    python3 .../names.py file.hoa|file.ltl  # whole HOA / per-line LTL
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict

_CANON = "abcdefghijklmnopqrstuvwxyz"
_KEYWORDS = {"true", "false"}
_LTL_TOKEN = re.compile(r"[a-z][A-Za-z0-9_]*")          # lowercase-initial = AP / const
_HOA_AP_LINE = re.compile(r'^(AP:\s*(\d+))((?:\s+"[^"]*")*)\s*$', re.MULTILINE)


def normalize_ltl(s: str) -> str:
    """Rename APs to a, b, c, … by first occurrence. No other change."""
    order: Dict[str, str] = {}

    def repl(m: "re.Match[str]") -> str:
        tok = m.group(0)
        if tok in _KEYWORDS:
            return tok
        if tok not in order:
            order[tok] = _CANON[len(order)]
        return order[tok]

    return _LTL_TOKEN.sub(repl, s)


def normalize_hoa(text: str) -> str:
    """Rewrite the `AP:` line's quoted names to canonical names in index order.
    Everything else (states, transitions, acceptance) is left byte-for-byte."""

    def repl(m: "re.Match[str]") -> str:
        head, k = m.group(1), int(m.group(2))
        names = " ".join(f'"{_CANON[i]}"' for i in range(k))
        return f"{head}{(' ' + names) if k else ''}"

    return _HOA_AP_LINE.sub(repl, text)


def _is_hoa_text(text: str) -> bool:
    for line in text.splitlines():
        if line.strip():
            return line.lstrip().startswith("HOA:")
    return False


def normalize_text(text: str) -> str:
    """Dispatch on content: a whole HOA automaton -> `normalize_hoa`, a single LTL
    formula -> `normalize_ltl`."""
    return normalize_hoa(text) if _is_hoa_text(text) else normalize_ltl(text)


def _normalize_file(p: Path) -> str:
    text = p.read_text(encoding="utf-8")
    if _is_hoa_text(text):
        return normalize_hoa(text)
    out = []
    for line in text.splitlines():
        body = line.split("#", 1)[0].strip()
        out.append(line if not body else line.replace(body, normalize_ltl(body)))
    return "\n".join(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
    else:
        p = Path(args[0])
        print(_normalize_file(p) if p.is_file() else normalize_ltl(args[0]))
