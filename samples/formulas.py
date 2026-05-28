# Interesting LTL formulas used during development
#
# See also the larger curated sets in the same directory:
#   f2_successes.py            – 100 formulas where the f2 heuristic activates
#   terminal_2scc_labeled.py   – 100 formulas where the t2 (terminal-2-SCC) heuristic activates
#
# Those can be fed directly to:  python3 evaluate.py -f samples/terminal_2scc_labeled.py ...

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
