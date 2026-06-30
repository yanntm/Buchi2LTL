"""Rule 4 left-arm cofactoring: φ U ψ ≡ φ' U ψ, φ' = restrict(φ, ¬ψ).
Every firing must be a language equivalence AND a strict shrink."""
import sys

import spot

from aut2ltl.ltl.simplify import fold_simplify, reset_caches
from aut2ltl.ltl.simplify.fold_pass import _arm_cofactor

CASES = [
    # (input, expected output shape or None for "just must be equiv+<=")
    ("(a & !b) U b", "a U b"),
    ("(a & !b) W b", "a W b"),
    ("(a | b) U b",  "a U b"),
    ("(a | !b) R b", "a R b"),
    ("(a | !b) M b", "a M b"),
    ("(a & !b & c) U b", "(a & c) U b"),
    # nested / under a temporal head — must still fire
    ("X((a & !b) U b)", "X(a U b)"),
    ("G((p & !q) U q)", "G(p U q)"),
    # no-op cases (must NOT change / stay equivalent)
    ("a U b", "a U b"),
    ("(a & c) U b", "(a & c) U b"),
]

fails = 0
for src, want in CASES:
    f = spot.formula(src)
    reset_caches()
    out = fold_simplify(f)
    eq = spot.are_equivalent(f, out)
    shape_ok = (str(out) == str(spot.formula(want)))
    if not eq or not shape_ok:
        fails += 1
        print(f"FAIL  {src!r}: out={out}  equiv={eq}  want={want}")
    else:
        print(f"ok    {src!r} -> {out}")

# direct unit checks of _arm_cofactor on the leaf operators
for src, want in [("(a & !b) U b", "a U b"), ("(a|!b) R b", "a R b")]:
    got = _arm_cofactor(spot.formula(src))
    if str(got) != str(spot.formula(want)):
        fails += 1
        print(f"FAIL  _arm_cofactor({src!r}) = {got}, want {want}")

print("RESULT:", "SUCCESS" if fails == 0 else f"{fails} FAILURES")
sys.exit(1 if fails else 0)
