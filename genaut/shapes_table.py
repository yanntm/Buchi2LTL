"""genaut/shapes_table.py — regenerate SHAPES.md from the corpus census.md files.

The per-shape census.md (written by gen/enumerate.py next to the samples) is the
source of truth for combos / byte-distinct / polarity-fold / kept. This scans every
corpus/<tag>/census.md, parses those numbers (no arithmetic here — just read what
generation recorded), and writes the SHAPES.md feasible-shapes table sorted by N.

  python3 genaut/shapes_table.py        # -> rewrites genaut/SHAPES.md
"""
from __future__ import annotations

import glob
import os
import re
from typing import Dict, List

HERE = os.path.dirname(__file__)
CORPUS = os.path.join(HERE, "corpus")
OUT = os.path.join(HERE, "SHAPES.md")
DEFERRED_KEPT = 1000          # kept above this is heavy to survey -> flagged "deferred"

_FIELDS = {
    "nstates": r"nstates=(\d+)", "naps": r"naps=(\d+)", "nacc": r"nacc=(\d+)",
    "slots": r"slots:\s*(\d+)", "combos": r"combos \(generator-id space N\):\s*(\d+)",
    "byte": r"byte-distinct \(md5[^)]*\):\s*(\d+)",
    "polarity": r"polarity/name twins folded:\s*(\d+)",
    "kept": r"kept \(AP-canonical survivors\):\s*(\d+)",
}


def parse_census(path: str) -> Dict[str, int]:
    text = open(path).read()
    row: Dict[str, int] = {}
    for name, pat in _FIELDS.items():
        m = re.search(pat, text)
        if not m:
            raise ValueError(f"{path}: field {name!r} not found")
        row[name] = int(m.group(1))
    row["tag"] = os.path.basename(os.path.dirname(path))
    return row


PROSE_HEAD = """# genaut shapes — the bestiary map

The shapes the census enumerates, and the tractability wall. A **shape** is
`Shape(n, k, c)` — `n` states, `k` atomic propositions, `c` acceptance sets (see
[`gen/algorithm.md`](gen/algorithm.md)). Each shape's generator-id space is

```
slots = n^2 * 2^c                      (one edge slot per (src, dst, markset))
N     = (2^(2^k)) ^ slots              (guards = all Boolean functions over k APs)
```

`N` is **doubly exponential in `k`**, exponential in `n^2` and `2^c`, so exhaustive
enumeration only reaches small shapes. Each row below is a one-off census written to
`corpus/<tag>/` with a `census.md`; **this table is generated from those census.md
files** (`python3 genaut/shapes_table.py`), not hand-kept.

## Feasible shapes (from corpus/*/census.md)

`kept` = distinct automata after both dedup gates (md5, then polarity o names);
`polarity` = relabel twins folded by the second gate. `survey`: most are surveyed
into `logs/<tag>/`; the high-`kept` ones (**deferred**) are heavy and run separately.
"""

PROSE_TAIL = """
## Beyond the wall (first intractable)

| shape | N | why |
|---|---|---|
| `2state2ap1acc` | 16^8 ~ 4.3e9 | the true k=2 analog of 2state1ap1acc |
| `1state2ap3acc` | 16^8 ~ 4.3e9 | |
| `1state3ap2acc` | 256^4 ~ 4.3e9 | |
| `3state2ap0acc` | 16^9 ~ 6.9e10 | |
| `3state1ap1acc` | 4^18 ~ 6.9e10 | 3-state with both an AP and acceptance |

## Reading the numbers

- **`k >= 1` only.** 0-AP shapes are excluded: a one-letter alphabet has a single
  ω-word, so the only languages are `0` and `1` — no linguistic content to census.
- **`k` drives the polarity fold**: the relabel group is `2^k * k!`, so the fold grows
  fast with APs.
- **The LTL frontier is `n >= 2` AND `k >= 1`**: counting needs a multi-state cycle
  over a real alphabet (a non-aperiodic monoid). 1-state shapes stay all-LTL; not-LTL
  first appears at `2state1ap0acc`.
- **Generation is cheap; surveying is not** — running `aut2ltl` over a shape's `kept`
  automata scales with `kept`, so the high-`kept` shapes are surveyed separately.
"""


def main() -> None:
    rows: List[Dict[str, int]] = [
        parse_census(p) for p in glob.glob(os.path.join(CORPUS, "*", "census.md"))]
    rows.sort(key=lambda r: (r["combos"], r["tag"]))
    lines = ["| shape | n | k | c | slots | N (combos) | byte-distinct | polarity "
             "| **kept** | survey |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        survey = "deferred" if r["kept"] > DEFERRED_KEPT else ""
        lines.append(
            f"| `{r['tag']}` | {r['nstates']} | {r['naps']} | {r['nacc']} "
            f"| {r['slots']} | {r['combos']} | {r['byte']} | {r['polarity']} "
            f"| **{r['kept']}** | {survey} |")
    with open(OUT, "w") as out:
        out.write(PROSE_HEAD + "\n" + "\n".join(lines) + "\n" + PROSE_TAIL)
    print(f"wrote {OUT} from {len(rows)} census.md files")


if __name__ == "__main__":
    main()
