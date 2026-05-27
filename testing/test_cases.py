"""
Collection of interesting LTL formulas and HOAs for testing the reconstruction.

This file is purely data + small helpers. It is not meant to be executed directly.
"""

# A set of formulas that worked reasonably well with the prototype at some point
KNOWN_REASONABLE_CASES = [
    "(p U q) & GF r",
    "FG a",
    "a U b",
    "G (p -> X p) & GF q",
]

# Formulas that are known to be problematic (produce wrong results or UNSUPPORTED)
KNOWN_PROBLEMATIC_CASES = [
    "!p1 W p0",
    "G!p2 R p1",
]

# The two HOAs the user provided during development
HOA_MOTIVATING_EXAMPLE = """HOA: v1
name: "(p U q) & GFr"
States: 2
Start: 0
AP: 3 "p" "q" "r"
acc-name: Buchi
Acceptance: 1 Inf(0)
properties: trans-labels explicit-labels trans-acc deterministic
--BODY--
State: 0
[0&!1] 0
[1] 1
State: 1
[!2] 1
[2] 1 {0}
--END--
"""

HOA_SECOND_EXAMPLE = """HOA: v1
name: "G(Fq & (!p | Xp))"
States: 2
Start: 0
AP: 2 "q" "p"
acc-name: Buchi
Acceptance: 1 Inf(0)
properties: trans-labels explicit-labels trans-acc deterministic
--BODY--
State: 0
[!0&!1] 0
[0&!1] 0 {0}
[1] 1
State: 1
[!0&1] 1
[0&1] 1 {0}
--END--
"""

# The very-weak / trivial acceptance example that motivated the empty-acc hack
HOA_VERY_WEAK_W_UNTIL = """HOA: v1
name: "!p1 W p0"
States: 2
Start: 1
AP: 2 "p1" "p0"
acc-name: all
Acceptance: 0 t
properties: trans-labels explicit-labels trans-acc deterministic
properties: stutter-invariant very-weak
--BODY--
State: 0
[t] 0
State: 1
[1] 0
[!0&!1] 1
--END--
"""


def load_hoa_as_automaton(hoa_text):
    """Helper to turn one of the HOA strings above into a Spot automaton."""
    import spot
    return spot.automaton(hoa_text)
