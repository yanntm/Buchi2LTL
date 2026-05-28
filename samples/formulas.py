# Interesting LTL formulas used during development

# Basic cases that worked well
BASIC = [
    "(p U q) & GF r",
    "FG a",
    "a U b",
    "G (p -> X p) & GF q",
]

# Cases that required the f2 (size-2 fusion) heuristic
F2_REQUIRED = [
    "X(p1 | F(p1 & Xp1))",
]

# Known problematic cases (very-weak, etc.)
PROBLEMATIC = [
    "!p1 W p0",
    "G!p2 R p1",
]
