"""Independent GF/FG sibling cofactoring (boolean args):
    GF φ ∧ FG ψ → GF(φ|ψ)  ∧ FG ψ
    FG α ∨ GF β → FG(α|¬β) ∨ GF β   (dual)
Every firing Spot-verified equivalent; must-not-fire guards included."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import spot
from aut2ltl.ltl.simplify import fold_simplify, reset_caches

CASES = [
    ("GF(a & b) & FG(b)",             "GF(a) & FG(b)"),
    ("GF(a & b & c) & FG(b) & FG(c)", "GF(a) & FG(b) & FG(c)"),
    ("GF(a | b) & FG(!b)",            "GF(a) & FG(!b)"),
    # dual on Or
    ("FG(a | b) | GF(b)",             "FG(a) | GF(b)"),
    ("FG(a & !b) | GF(b)",            "FG(a) | GF(b)"),
    # nested under another temporal
    ("X(GF(a & b) & FG(b))",          "X(GF(a) & FG(b))"),
    # strong until/release as invariant SOURCE (φ U G(x) ⟹ FG x; dual φ R F(x))
    ("GF(a & b) & (c U G(b))",        "GF(a) & (c U G(b))"),
    ("FG(a | b) | (c R F(b))",        "FG(a) | (c R F(b))"),
    # must NOT fire: WEAK until/release give no eventuality (Gφ / G¬φ branch)
    ("GF(a & b) & (c W G(b))",        "GF(a & b) & (c W G(b))"),
    ("FG(a | b) | (c M F(b))",        "FG(a | b) | (c M F(b))"),
    # must NOT fire: no FG sibling
    ("GF(a & b) & GF(b)",             "GF(a & b) & GF(b)"),
    # must NOT fire: GF arg not propositional
    ("GF(a & Xb) & FG(b)",            "GF(a & Xb) & FG(b)"),
]

fails = 0
for src, want in CASES:
    reset_caches()
    f = spot.formula(src)
    out = fold_simplify(f)
    eq = spot.are_equivalent(f, out)
    shape_ok = (out == spot.formula(want))
    if not (eq and shape_ok):
        fails += 1
        print(f"FAIL  {src!r} -> {out}  (equiv={eq}, want {want})")
    else:
        print(f"ok    {src!r} -> {out}")

print("RESULT:", "SUCCESS" if not fails else f"{fails} FAILURES")
sys.exit(1 if fails else 0)
