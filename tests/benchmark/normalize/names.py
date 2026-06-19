"""normalize.py — AP-canonical NAME form, the benchmark dedup key.

It does ONE thing: rename atomic propositions to a, b, c, … in order of first
occurrence. It does NOT simplify (no logical/syntactic rewrites), does NOT
reorder commutative operands, does NOT minimise automata. So two inputs that
differ only by AP names normalise to the same string, and an exact-text compare
of normalised forms is a sound, conservative syntactic dedup key.

- LTL  : token-level rename over the formula string (lowercase-initial tokens,
  minus the `true`/`false` constants). Operators are uppercase / symbolic, so
  they are never touched.
- HOA  : rewrite the quoted names on the `AP:` preamble line to canonical names
  in index order. Transitions reference APs by index, so this is purely cosmetic
  — a WEAK key: it collapses name-variants and exact-duplicate automata, but NOT
  automata that are equal up to state renumbering / transition reordering (that
  needs real iso — a curation-phase concern, deliberately out of scope here).

CLI:
    python3 tests/benchmark/normalize.py '<formula>'      # print normalised LTL
    python3 tests/benchmark/normalize.py file.hoa|file.ltl
    python3 tests/benchmark/normalize.py --dedup PATHS...  # report dup groups
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

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


def normalized_keys(path: Path) -> List[Tuple[str, str]]:
    """(item-id, normalised-form) for an input file: one entry for a HOA file,
    one per non-comment formula line for an .ltl file."""
    text = path.read_text(encoding="utf-8")
    if _is_hoa_text(text):
        return [(str(path), normalize_hoa(text))]
    out: List[Tuple[str, str]] = []
    for line in text.splitlines():
        f = line.split("#", 1)[0].strip()
        if f:
            out.append((f, normalize_ltl(f)))
    return out


def _dedup(paths: List[str]) -> None:
    groups: Dict[str, List[str]] = {}
    for p in paths:
        for item_id, key in normalized_keys(Path(p)):
            groups.setdefault(key, []).append(item_id)
    total = sum(len(v) for v in groups.values())
    print(f"{total} items -> {len(groups)} unique (normalised)")
    for key, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(members) > 1:
            print(f"  x{len(members)}: {members[0]}  (+{len(members) - 1} more)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--dedup":
        _dedup(args[1:])
    elif args:
        a = args[0]
        p = Path(a)
        if p.is_file():
            t = p.read_text(encoding="utf-8")
            print(normalize_hoa(t) if _is_hoa_text(t)
                  else "\n".join(k for _, k in normalized_keys(p)))
        else:
            print(normalize_ltl(a))
    else:
        print(__doc__)
