"""Wall-time-bounded translate, run as a fresh subprocess.

Reads one formula string on argv, runs the SAME in-process binding the unbounded
path uses (`formula.translate()`), and writes its automaton as HOA to stdout. Using
the binding here — not the `ltl2tgba` CLI — keeps the bounded result structurally
identical to the unbounded one, so bounding a translate never changes the
reconstruction, only kills a runaway. Invoked by `spotrun.translate` via
`aut2ltl.bounded`; kept minimal (imports spot only) so the child is cheap to spawn.
"""
import sys

import spot


def main() -> int:
    f = spot.formula(sys.argv[1])
    sys.stdout.write(f.translate().to_str("hoa"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
