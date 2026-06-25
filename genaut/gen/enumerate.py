"""genaut/gen/enumerate.py — exhaustive generation driver for a chosen Shape.

For a Shape (states/APs/acc sets) this enumerates every combo of the slot model
(shape.combo_at order), runs one spot.postprocess(Small, Generic) pass on each,
and applies the two pre-write dedup gates — byte-identical md5, then the shared
AP-canonical key (polarity o names) from survey.normalize — before writing one HOA
per survivor to genaut/raw/<tag>/<tag>_<id>.hoa (the file carries its own shape, so
it is self-identifying out of its folder). A twin is never built into a file. See
algorithm.md.

Usage:
  python3 genaut/gen/enumerate.py [SHAPE] [LIMIT]
    SHAPE  nstates,naps,nacc   (default 2,1,1 — the legacy census)
    LIMIT  smoke-test the first N combos only
"""
from __future__ import annotations

import hashlib
import itertools
import os
import shutil
import sys
from typing import Callable, Optional, Set

import spot

# sibling modules (run as a path-script: genaut/gen is sys.path[0])
from shape import Shape
from build import build_aut, reduce_aut

RAW_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), os.pardir, "raw"))


def _ap_canonical_key() -> "Callable[[str], str]":
    """The shared AP-canonical dedup key (polarity o names) from survey.normalize,
    reached by putting the repo root on sys.path. Trusted sound for any produced
    TGBA, so it carries to every shape (see algorithm.md)."""
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from survey.normalize.dedup import default_key
    return default_key


def parse_shape(token: str) -> Shape:
    parts = token.split(",")
    if len(parts) != 3:
        raise ValueError(f"shape must be 'nstates,naps,nacc', got {token!r}")
    n, k, c = (int(p) for p in parts)
    return Shape(n, k, c)


def main(shape: Shape, limit: Optional[int]) -> None:
    if shape.naps < 1:                  # 0-AP = one-letter alphabet: only 0/1, no content
        raise SystemExit(f"{shape.tag}: 0-AP shapes are linguistically empty "
                         "(the only languages are 0 and 1) — not censused.")
    out_dir = os.path.join(RAW_ROOT, shape.tag)
    shutil.rmtree(out_dir, ignore_errors=True)   # start clean: no stale survivors
    os.makedirs(out_dir, exist_ok=True)
    bdict = spot.make_bdd_dict()
    ap_key = _ap_canonical_key()

    combos = itertools.product(shape.guards, repeat=len(shape.slots))
    width = shape.id_width                  # zero-pad just enough for the id space
    seen_md5: Set[str] = set()             # byte-identical HOA
    seen_key: Set[str] = set()             # AP-canonical key (polarity o names)
    total = written = folded = 0
    for i, combo in enumerate(combos):
        if limit is not None and i >= limit:
            break
        total += 1
        content = reduce_aut(build_aut(shape, combo, bdict)).to_str("hoa") + "\n"
        digest = hashlib.md5(content.encode()).hexdigest()
        if digest in seen_md5:             # byte-identical to an earlier id -> drop
            continue
        seen_md5.add(digest)
        key = ap_key(content)              # only the byte-distinct survivors pay this
        if key in seen_key:                # AP-canonical twin of an earlier id -> drop
            folded += 1
            continue
        seen_key.add(key)
        with open(os.path.join(out_dir, f"{shape.tag}_{i:0{width}d}.hoa"), "w") as out:
            out.write(content)
        written += 1
        if total % 5000 == 0:
            print(f"  ... {total} scanned, {written} kept", file=sys.stderr)

    _write_census(out_dir, shape, total, len(seen_md5), folded, written)
    print(f"[{shape.tag}] scanned {total} combos, kept {written} AP-canonical "
          f"distinct ({len(seen_md5)} byte-distinct, {folded} polarity/name twins "
          f"folded pre-write) -> {out_dir}/{shape.tag}_NNNNN.hoa")


def _write_census(out_dir: str, shape: Shape, combos: int, byte_distinct: int,
                  folded: int, kept: int) -> None:
    """Write census.md next to the generated files — the set-info for this shape,
    so its stats need no rerun. Markdown (not .txt) so the survey's --folder
    discovery, which reads .ltl/.txt as LTL lists, skips it; GitHub renders it."""
    text = (
        f"# {shape.tag} — generation census\n\n"
        f"- shape: nstates={shape.nstates}, naps={shape.naps}, nacc={shape.nacc}\n"
        f"- guard alphabet: {len(shape.guards)} boolean functions over {shape.naps} "
        f"AP(s) (incl. false = edge absent)\n"
        f"- slots: {len(shape.slots)}  (= nstates^2 x 2^nacc)\n"
        f"- combos (generator-id space N): {combos}\n"
        f"- byte-distinct (md5, after Spot reduction): {byte_distinct}\n"
        f"- polarity/name twins folded: {folded}\n"
        f"- **kept (AP-canonical survivors): {kept}**\n"
        f"- file naming: `{shape.tag}_<id>.hoa` (id width {shape.id_width})\n\n"
        f"Generated by `python3 genaut/gen/enumerate.py "
        f"{shape.nstates},{shape.naps},{shape.nacc}`.\n"
        f"Reconstructed languages/formulas: see the survey run under "
        f"`genaut/logs/{shape.tag}/`.\n")
    with open(os.path.join(out_dir, "census.md"), "w") as out:
        out.write(text)


if __name__ == "__main__":
    args = sys.argv[1:]
    shp = parse_shape(args[0]) if args else Shape(2, 1, 1)
    lim = int(args[1]) if len(args) > 1 else None
    main(shp, lim)
