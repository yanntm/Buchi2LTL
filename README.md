# BuchiToLTL

Experimental prototype for backward LTL reconstruction from Transition-based Generalized Büchi Automata (TGBA).

## Current Status

This is research / exploration code. The reconstruction is **incomplete by design**.

We now have two heuristics that can rescue certain formulas whose automata contain a size-2 SCC:

* **f2** – size-2 non-accepting SCC absorption ("fusion test")
* **t2** – terminal 2-state accepting SCC pattern matching (new)

When either succeeds (and passes an internal language-equivalence soundness check on the isolated fragment), formulas that used to be reported `UNSUPPORTED` become fully reconstructible.

Key current capabilities:
- Explicit recursion with visiting set + depth limit (finite recursion)
- Early rejection of multi-state SCCs (unless a heuristic has already validated a fragment for them)
- Size-2 non-accepting SCC absorption (f2) when language-equivalent
- Terminal 2-state accepting SCC steady-state extraction (t2) via incoming/outgoing label disjunction + round-trip validation
- Trivial acceptance normalization (treat all transitions as accepting when `Acceptance: t`)
- "Technique" reporting: `sl`, `sl+f2`, `sl+t2`, `sl+f2+t2`
- Dual output: constructive formula + version after Spot simplification (`ltlfilt` equivalent)
- Detailed tracing of the t2 path under `RECONSTRUCT_TRACE=1`

## Project Organization

```
buchi2ltl.py                  # Thin CLI / backward-compat entry point
buchi2ltl/                    # Main package
    __init__.py               # Public API (reconstruct_ltl + both heuristics)
    reconstruction.py         # Core reconstruct_ltl + labeling logic (now integrates f2 + t2)
    heuristics/
        size2_overapprox.py   # Size-2 non-accepting SCC absorption ("f2"/"fusion")
        terminal_2scc.py      # Terminal 2-state SCC pattern ("t2") – heavily documented
    utils.py                  # simplify_ltl() etc. (currently bypassed for raw debug output)
evaluate.py                   # Evaluation harness (stable samples + random round-trip testing)
samples/                      # Curated LTL formulas and HOAs (for regression / stable testing)
testing/                      # Heavy debugging and experimental scripts
    visualize_fusion.py       # Automaton visualization helper (before/after)
    inspect_failures.py
    ...
README.md
```

## Quick Start

```bash
python3 buchi2ltl.py
```

Runs a small set of formulas (including both f2 and t2 cases) and shows:
- Original vs recovered LTL
- **Technique** used (`sl`, `sl+f2`, `sl+t2`, or `sl+f2+t2`)
- Equivalence result
- Constructive formula + simplified version

## Evaluation Harness

`evaluate.py` is the main tool for batch testing the reconstruction.

It supports **stable test sets** (important for regression work) in addition to random generation:

```bash
# Run only the curated samples from samples/formulas.py (stable set)
python3 evaluate.py --samples --no-random -o stable.csv

# Curated samples + 200 random formulas afterwards
python3 evaluate.py --samples -n 200 --seed 42 -o mixed.csv

# Load your own formulas (Python file with lists, or plain text one-per-line)
python3 evaluate.py -f my_hard_cases.py --no-random -o custom.csv

# Classic random-only mode (still fully supported)
python3 evaluate.py -n 500 --seed 7 --aps 3 -o results.csv
```

Key features:
- Explicit formulas are always processed **first** (stable ordering).
- Output CSV includes a `source` column (`samples/formulas.py`, `random(seed=42)`, or `file:yourfile.txt`).
- `UNSUPPORTED` cases are recorded cleanly as `equivalent=unsupported` instead of noisy errors.
- Use `--only-failures` to collect interesting cases.

See `python3 evaluate.py --help` for all options.

The `samples/` directory contains hand-curated formulas, including:
- `formulas.py` – the default set used by `evaluate.py --samples`
- `f2_successes.py` – 100 formulas for which the f2 heuristic activates
- `terminal_2scc_labeled.py` – 100 formulas for which the t2 heuristic activates

You can feed any of them directly to the evaluation harness:

    python3 evaluate.py -f samples/terminal_2scc_labeled.py --no-random -o t2_only.csv

Example HOAs for manual inspection live alongside them.

## Public API

```python
from buchi2ltl import reconstruct_ltl, try_size2_overapprox, try_terminal_2scc_with_validation, simplify_ltl

recovered, state_labels, technique = reconstruct_ltl(aut)

# Or call a heuristic in isolation (mainly for diagnostics / external tools)
nice = try_terminal_2scc_with_validation(aut)   # list of validated t2 fragments
```

## Notes

- Many formulas will still return `"UNSUPPORTED: ..."` (especially those with complex SCCs or entry-choice asymmetries into a terminal SCC).
- Two heuristics can now rescue size-2 SCCs:
  - `f2` – size-2 non-accepting SCC absorption (older, absorption-style)
  - `t2` – terminal 2-state accepting SCC pattern (new, G(L & X O | ...) style)
- Both heuristics only accept a candidate after a full Spot `are_equivalent` round-trip on the isolated fragment (soundness first).
- Detailed per-state traces for the t2 integration are emitted only when the environment variable `RECONSTRUCT_TRACE=1` is set (very verbose – intended for debugging the reconstruction rules themselves).
- All Spot simplification is currently bypassed (`simplify_ltl` is a no-op) so that the raw structure built by the labeler remains visible. Re-enable it in `buchi2ltl/utils.py` when you want the final "ltlfilt --simplify" look.
- Generated images (`*.png`, `*.dot`) and all `*.csv` / `*.log` files are gitignored.
- `testing/` contains the heavy experimental scaffolding:
  - `recovered_working_fusion_heuristic.py` – exact historical f2 code that produced the early debug images
  - `initial_state_rewiring.py` – the initial-state split experiment (kept because the user asked to preserve it even though it is no longer called from the production path)
  - `find_*.py` – the search scripts used to populate the stable 100-formula sample sets
- The historical recovered fusion file is in `testing/`, not `samples/`.

This repository is used for interactive development of the reconstruction technique. The t2 pattern is known to need further refinement (especially around prefix entry choice into the SCC – see development log for the "r U G(!p | Xq)" example).
