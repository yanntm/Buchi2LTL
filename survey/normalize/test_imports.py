"""Guard the package's public surface the way the sibling collectors import it:
they put `tests/benchmark` on sys.path and do `from normalize import ...`.

Run: python3 tests/benchmark/normalize/test_imports.py   (prints OK / raises)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Mimic the collectors: tests/benchmark on the path, import the package by name.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from normalize import (  # noqa: E402
    _is_hoa_text,
    normalize_hoa,
    normalize_ltl,
    polarity_normalize_hoa,
    polarity_normalize_ltl,
)

assert normalize_ltl("p & q") == "a & b"
assert polarity_normalize_ltl("!p & q") == "p & q"
assert _is_hoa_text("HOA: v1\n")
assert callable(normalize_hoa) and callable(polarity_normalize_hoa)

print("OK")
