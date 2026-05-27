# BuchiToLTL

Experimental prototype for backward LTL reconstruction from Transition-based Generalized Büchi Automata (TGBA).

## Current Status

This is research / exploration code. The reconstruction is **incomplete by design**.

The current best version of the reconstruction lives in `buchi2ltl.py` (`reconstruct_ltl`).

Key features of the current implementation:
- Explicit recursion with a visiting set + hard depth limit (guaranteed finite recursion)
- Early rejection of automata containing multi-state SCCs
- Pragmatic normalization for trivial-acceptance automata (`Acceptance: t`): every transition is treated as accepting
- Reconstruction rules based on manual backward labeling from accepting self-loops

## Project Organization

```
buchi2ltl.py          # Core reconstruction logic + small manual test entry point
testing/              # Experimental and debugging code (not part of the stable surface)
    test_cases.py     # Collections of interesting formulas and HOAs
    debug_empty_acc.py
    test_safe_reconstruction.py
    ...
README.md
```

## Quick Start

```bash
python3 buchi2ltl.py
```

This will run a few classic LTL formulas through `ltl_to_tgba` + `reconstruct_ltl` and report results.

## Notes

- The main entry point is intentionally minimal. Most serious testing lives under `testing/`.
- Many formulas will return `"UNSUPPORTED: ..."` or semantically incorrect results.
- The empty-acceptance normalization (treating all transitions as accepting when there are 0 acceptance sets) was added to handle very-weak automata (e.g. those produced by weak until).

This repository is currently used for interactive development and algorithm exploration.
