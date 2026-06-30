"""Independent W/M expansion fold in fold_pass:
    G f       ∨ (f U g)  → f W g       (and the ¬g-strengthened body)
    F f       ∧ (f R g)  → f M g       (dual)
    G g       ∨ (f M g)  → f R g       (M-disjunct sibling of the W-fold)
    F g       ∧ (f W g)  → f U g       (dual of the R-fold; completes the quartet)
Every firing must be a Spot-verified language equivalence; must-not-fire
cases guard against the unsound extra-conjunct variant."""
import sys
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
    # R-fold (M-disjunct sibling of the W-fold): G g ∨ (f M g) → f R g
    ("Ge | (d M e)",                        "d R e"),
    ("G(!d & e) | (d M e)",                 "d R e"),                # the trace
    ("G(p & q) | (r M (p & q))",            "r R (p & q)"),          # g compound
    ("G(Gq & !(Fp)) | (Fp M Gq)",           "Fp R Gq"),              # temporal f,g
    # U-fold (W-conjunct sibling, dual of R-fold): F g ∧ (f W g) → f U g
    ("Fe & (d W e)",                        "d U e"),
    ("F(!d | e) & (d W e)",                 "d U e"),                # ¬f-weakened body
    ("F(p & q) & (r W (p & q))",            "r U (p & q)"),          # g compound
    ("F(Gq | !(Fp)) & (Fp W Gq)",           "Fp U Gq"),              # temporal f,g
    # must NOT fire (extra conjunct -> G body strictly stronger): unchanged
    ("G(!b & h & c) | (h U b)",             "G(c & h & !b) | (h U b)"),
    ("G(!d & e & c) | (d M e)",             "G(c & e & !d) | (d M e)"),
    # must NOT fire (extra disjunct -> F body strictly weaker): unchanged
    ("F(e | d | c) & (d W e)",              "(d W e) & F(c | d | e)"),
    # must NOT fire: G body unrelated to U left arm
    ("G(p & q) | (p U r)",                  "G(p & q) | (p U r)"),
    # must NOT fire: G body unrelated to M right arm
    ("G(p & q) | (r M p)",                  "G(p & q) | (r M p)"),
    # must NOT fire: F body unrelated to W right arm
    ("F(p & q) & (r W p)",                  "(r W p) & F(p & q)"),
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
