"""Independent W/M expansion fold in fold_pass:
    G f       ∨ (f U g)  → f W g       (and the ¬g-strengthened body)
    F f       ∧ (f R g)  → f M g       (dual)
Every firing must be a Spot-verified language equivalence; must-not-fire
cases guard against the unsound extra-conjunct variant."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import spot
from aut2ltl.ltl.simplify import fold_simplify, reset_caches

# (input, expected_shape)
CASES = [
    # W-fold
    ("Gh | (h U b)",                        "h W b"),
    ("G(!b & h) | (h U b)",                 "h W b"),
    ("G(c & !d) | (c U d)",                 "c W d"),
    ("G(p & q) | ((p & q) U r)",            "(p & q) W r"),          # f compound
    ("G(Xp & !(q U r)) | (Xp U (q U r))",   "Xp W (q U r)"),         # temporal f,g
    # M-fold (dual)
    ("Fa & (a R b)",                        "a M b"),
    ("F(a | !b) & (a R b)",                 "a M b"),
    ("F(Fp | !(Gq)) & (Fp R Gq)",           "Fp M Gq"),              # temporal dual
    # must NOT fire (extra conjunct -> G body strictly stronger): unchanged
    ("G(!b & h & c) | (h U b)",             "G(c & h & !b) | (h U b)"),
    # must NOT fire: G body unrelated to U left arm
    ("G(p & q) | (p U r)",                  "G(p & q) | (p U r)"),
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
