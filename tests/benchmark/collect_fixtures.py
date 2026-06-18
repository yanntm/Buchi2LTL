"""collect_fixtures.py — port the dev fixtures (tests/fixtures) into the benchmark.

The dev-time fixture corpus lives as Python data lists in `tests/fixtures/*.py`
(BASIC / F2_SUCCESS / T2_SUCCESS / TERMINAL_2SCC_LABELED, …) plus three raw `.hoa`
files. This brings them into the file-based benchmark tree, ONE source list ->
one `inputs/fixtures/<stem>.ltl`, and the three HOA fixtures copied verbatim.

Dedup is cumulative and file-by-file: the AP-normalized key
(`normalize.normalize_ltl`) of every formula already present anywhere in the
benchmark inputs (EXCLUDING `inputs/kinska/`, and excluding the file currently
being (re)written) is collected first; a formula whose key is already present is
NOT re-added. So you import one list at a time, in order, and each later import
skips whatever earlier ones already contributed — the corpus stays
duplicate-free as it grows. The basic AP rename (normalize_ltl / normalize_hoa)
is APPLIED to what we store, so every emitted example is in canonical a,b,c… form
— that is the only change; no simplification, no reordering.

Run one import at a time:
    python3 tests/benchmark/collect_fixtures.py formulas
    python3 tests/benchmark/collect_fixtures.py f2_successes
    python3 tests/benchmark/collect_fixtures.py t2_successes
    python3 tests/benchmark/collect_fixtures.py terminal_2scc
    python3 tests/benchmark/collect_fixtures.py hoa
    python3 tests/benchmark/collect_fixtures.py all        # every import, in order
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Callable, Dict, List, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import normalize_hoa, normalize_ltl  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests/fixtures"
INPUTS = ROOT / "tests/benchmark/inputs"
DST = INPUTS / "fixtures"

# A "section" is a titled run of formulas inside one output file.
Section = Tuple[str, List[str]]


def _load(module_file: str) -> object:
    """Import a `tests/fixtures/*.py` data module by path (no package needed)."""
    path = FIX / module_file
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _formulas_sections() -> List[Section]:
    m = _load("formulas.py")
    return [
        ("Basic cases that worked well", list(m.BASIC)),
        ("Required the size-2 fusion (f2) heuristic", list(m.F2_REQUIRED)),
        ("Known problematic (very-weak, etc.)", list(m.PROBLEMATIC)),
    ]


def _single(module_file: str, attr: str, title: str) -> Callable[[], List[Section]]:
    return lambda: [(title, list(getattr(_load(module_file), attr)))]


# import-key -> (output stem, id-tag prefix, source module, section provider)
LTL_IMPORTS: Dict[str, Tuple[str, str, str, Callable[[], List[Section]]]] = {
    "formulas": ("formulas", "fx", "formulas.py", _formulas_sections),
    "f2_successes": ("f2_successes", "f2", "f2_successes.py",
                     _single("f2_successes.py", "F2_SUCCESS",
                             "f2 (size-2 fusion) successes")),
    "t2_successes": ("t2_successes", "t2", "t2_successes.py",
                     _single("t2_successes.py", "T2_SUCCESS",
                             "tN terminal-SCC successes")),
    "terminal_2scc": ("terminal_2scc", "term", "terminal_2scc_labeled.py",
                      _single("terminal_2scc_labeled.py", "TERMINAL_2SCC_LABELED",
                              "labeled terminal 2-SCC candidates")),
}

# fixture .hoa file -> output name (kept descriptive; verbatim content).
HOA_IMPORTS: Dict[str, str] = {
    "motivating_example.hoa": "motivating_example.hoa",
    "second_example.hoa": "second_example.hoa",
    "very_weak_w_until.hoa": "very_weak_w_until.hoa",
}


def _existing_keys(exclude: Path | None) -> Set[str]:
    """Normalized keys of every benchmark `.ltl` formula already on disk, minus
    `inputs/kinska/` and the file we are about to (re)write."""
    keys: Set[str] = set()
    for p in sorted(INPUTS.rglob("*.ltl")):
        if "kinska" in p.parts or (exclude and p == exclude):
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            f = line.split("#", 1)[0].strip()
            if f:
                keys.add(normalize_ltl(f))
    return keys


def import_ltl(key: str) -> None:
    stem, prefix, source, provider = LTL_IMPORTS[key]
    out = DST / f"{stem}.ltl"
    seen = _existing_keys(exclude=out)
    DST.mkdir(parents=True, exist_ok=True)

    kept_sections: List[Tuple[str, List[str]]] = []
    kept = dropped = 0
    for title, formulas in provider():
        kept_here: List[str] = []
        for f in formulas:
            f = f.strip()
            if not f:
                continue
            k = normalize_ltl(f)
            if k in seen:
                dropped += 1
                continue
            seen.add(k)          # also dedups repeats within this import
            kept_here.append(k)  # store the AP-normalized form
            kept += 1
        kept_sections.append((title, kept_here))

    lines = [
        f"# Ported from tests/fixtures/{source} by tests/benchmark/collect_fixtures.py "
        f"-- do not hand-edit.",
        "# AP-renamed to canonical a,b,c… (normalize_ltl); dedup vs the rest of "
        "inputs/ (excl. kinska); no simplification.",
        "",
    ]
    n = 0
    for title, formulas in kept_sections:
        if not formulas:
            continue
        lines.append(f"# -- {title} --")
        for f in formulas:
            n += 1
            lines.append(f"{f}  # {prefix}{n:03d}")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"{stem}.ltl: {kept} kept, {dropped} dropped as dups (already in benchmark)")


def import_hoa() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    for src, dst in HOA_IMPORTS.items():
        text = (FIX / src).read_text(encoding="utf-8")
        (DST / dst).write_text(normalize_hoa(text), encoding="utf-8")   # AP-renamed
    print(f"hoa: {len(HOA_IMPORTS)} files AP-normalized -> {DST.relative_to(ROOT)}")


def main(argv: List[str]) -> int:
    if len(argv) != 1 or argv[0] not in {*LTL_IMPORTS, "hoa", "all"}:
        print(__doc__)
        return 2
    sel = argv[0]
    if sel == "all":
        for k in LTL_IMPORTS:
            import_ltl(k)
        import_hoa()
    elif sel == "hoa":
        import_hoa()
    else:
        import_ltl(sel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
