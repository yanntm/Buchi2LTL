"""spot_EU_rules.eu_simplify: the always-applied (≡) eventual/universal rules.

Each fire case asserts both a Spot language equivalence AND the expected folded
shape; the must-not-fire cases guard the class guards (wrong polarity / not
suspendable / right-arm not eventual|universal)."""
import sys
import spot
from aut2ltl.ltl.simplify.spot_EU_rules import eu_simplify, reset_cache

# (input, expected_shape)
CASES = [
    # --- fire: unary ---
    ("F(GFa)",        "GFa"),      # F e ≡ e     (e = GFa)
    ("F(Fa)",         "Fa"),       # F e ≡ e
    ("G(FGa)",        "FGa"),      # G u ≡ u
    ("G(Ga)",         "Ga"),       # G u ≡ u
    ("X(GFa)",        "GFa"),      # X q ≡ q
    ("X(FGa)",        "FGa"),      # X q ≡ q
    # --- fire: binary ---
    ("a U Fb",        "Fb"),       # f U e ≡ e
    ("a U GFb",       "GFb"),      # f U e ≡ e
    ("a R Gb",        "Gb"),       # f R u ≡ u
    ("a R FGb",       "FGb"),      # f R u ≡ u
    ("Ga W b",        "Ga | b"),   # u W g ≡ u ∨ g
    ("Fa M b",        "Fa & b"),   # e M g ≡ e ∧ g
    # --- fire: X-rotation (suspendable left) ---
    ("GFa U Xb",      "X(GFa U b)"),   # q U X g ≡ X(q U g)
    ("GFa R Xb",      "X(GFa R b)"),   # q R X g ≡ X(q R g)
    # --- fire: nested (rule cascades bottom-up) ---
    ("c U (a U Fb)",  "Fb"),       # inner→Fb, then c U Fb→Fb
    ("X(X(GFa))",     "GFa"),      # X X q ≡ q
    # --- must NOT fire ---
    ("a U b",         "a U b"),    # b not eventual
    ("a R b",         "a R b"),    # b not universal
    ("Fa W b",        "Fa W b"),   # Fa eventual but NOT universal -> W needs u
    ("a M b",         "a M b"),    # a not eventual -> M needs e
    ("Fa U Xb",       "Fa U Xb"),  # Fa not suspendable, Xb not eventual
    ("X a",           "X a"),      # a not suspendable
]

fails = 0
for src, want in CASES:
    reset_cache()
    f = spot.formula(src)
    out = eu_simplify(f)
    eq = spot.are_equivalent(f, out)
    shape_ok = (out == spot.formula(want))
    if not (eq and shape_ok):
        fails += 1
        print(f"FAIL  {src!r} -> {out}  (equiv={eq}, want {want})")
    else:
        print(f"ok    {src!r} -> {out}")

print("RESULT:", "SUCCESS" if not fails else f"{fails} FAILURES")
sys.exit(1 if fails else 0)
