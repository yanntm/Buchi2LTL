"""polarity.py — canonicalise per-AP polarity (a benchmark dedup key; does ONLY
polarity, nothing else: no renaming, no simplification, no reordering).

Each AP is complemented wherever its FIRST literal occurrence, in left-to-right
reading order, is negative — so the first occurrence comes out positive. Nothing
else changes (no renaming, no simplification, no reordering). Thus

    !a X F a   and   a X F !a    both -> a X F !a

and a HOA whose first edge to touch AP 0 reads `!0` collapses to its `0`-form.

- `polarity_normalize_ltl(formula)` / `polarity_normalize_hoa(text)` — the two
  variants; `polarity_normalize_text` dispatches on HOA-vs-LTL.
- `ltl_flips(s)` / `hoa_flips(text)` — the per-AP flip decision, exposed.

An AP is a lowercase-initial token in LTL (`true`/`false` exempt; symbolic
operators assumed) or an integer index inside a HOA `[...]` label (explicit APs,
no aliases). A negated literal is a `!` directly abutting the atom (`!a`, not
`!(a)`); `!!x` is out of scope. For HOA the reading order is the file's edge
order, so polarity is canonicalised relative to the presented form.

CLI:
    python3 tests/benchmark/polarity.py '<formula>'        # print polarity-canon LTL
    python3 tests/benchmark/polarity.py file.hoa|file.ltl  # whole HOA / per-line LTL
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import re

_KEYWORDS = {"true", "false"}
_LTL_LIT = re.compile(r"(!?)([a-z][A-Za-z0-9_]*)")   # (optional bang)(AP / const)
_HOA_LABEL = re.compile(r"\[([^\]]*)\]")             # a transition label expression
_HOA_LIT = re.compile(r"(!?)(\d+)")                  # (optional bang)(AP index)


# --- LTL -------------------------------------------------------------------

def ltl_flips(s: str) -> Dict[str, bool]:
    """AP token -> True iff its first literal occurrence is negated (so it must be
    complemented everywhere to make that first occurrence positive)."""
    flip: Dict[str, bool] = {}
    for m in _LTL_LIT.finditer(s):
        bang, tok = m.group(1), m.group(2)
        if tok in _KEYWORDS or tok in flip:
            continue
        flip[tok] = bool(bang)
    return flip


def polarity_normalize_ltl(s: str) -> str:
    """Complement every AP whose first occurrence is negated. Byte-precise: only
    the bangs of flipped APs change; all other text is returned verbatim."""
    flip = ltl_flips(s)

    def repl(m: "re.Match[str]") -> str:
        bang, tok = m.group(1), m.group(2)
        if tok in _KEYWORDS or not flip.get(tok, False):
            return m.group(0)
        return tok if bang else "!" + tok      # single-pass sign swap, no sentinel

    return _LTL_LIT.sub(repl, s)


# --- HOA -------------------------------------------------------------------

def hoa_flips(text: str) -> Dict[int, bool]:
    """AP index -> True iff its first literal occurrence (scanning `[...]` labels
    in file order, left-to-right within each) is negated."""
    flip: Dict[int, bool] = {}
    for lab in _HOA_LABEL.finditer(text):
        for m in _HOA_LIT.finditer(lab.group(1)):
            k = int(m.group(2))
            if k not in flip:
                flip[k] = bool(m.group(1))
    return flip


def polarity_normalize_hoa(text: str) -> str:
    """Complement every AP index whose first label occurrence is negated. Only the
    contents of `[...]` labels are touched; states, acceptance, preamble verbatim."""
    flip = hoa_flips(text)

    def lit_repl(m: "re.Match[str]") -> str:
        bang, idx = m.group(1), m.group(2)
        if not flip.get(int(idx), False):
            return m.group(0)
        return idx if bang else "!" + idx

    def lab_repl(lab: "re.Match[str]") -> str:
        return "[" + _HOA_LIT.sub(lit_repl, lab.group(1)) + "]"

    return _HOA_LABEL.sub(lab_repl, text)


# --- dispatch / CLI --------------------------------------------------------

def _is_hoa_text(text: str) -> bool:
    for line in text.splitlines():
        if line.strip():
            return line.lstrip().startswith("HOA:")
    return False


def polarity_normalize_text(text: str) -> str:
    """Whole-input convenience: HOA automaton -> `polarity_normalize_hoa`, a single
    LTL formula -> `polarity_normalize_ltl`. (For multi-formula `.ltl` files,
    canonicalise per line — each formula's first occurrence is independent.)"""
    return polarity_normalize_hoa(text) if _is_hoa_text(text) \
        else polarity_normalize_ltl(text)


def _normalize_file(p: Path) -> str:
    text = p.read_text(encoding="utf-8")
    if _is_hoa_text(text):
        return polarity_normalize_hoa(text)
    out = []
    for line in text.splitlines():
        body = line.split("#", 1)[0].strip()
        out.append(line if not body else line.replace(body, polarity_normalize_ltl(body)))
    return "\n".join(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
    else:
        p = Path(args[0])
        print(_normalize_file(p) if p.is_file() else polarity_normalize_ltl(args[0]))
