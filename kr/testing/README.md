# kr/testing/

Internal development and verification scripts for the Krohn-Rhodes (kr/) experimental path.

## Purpose
- Verify the clean vs. heuristic reconstruction after the refactor (moving away from ad-hoc structural pattern matching in `reconstruct_ltl_1level_buchi`).
- Test stability improvements (BDD var precomputation in `bdd_utils.py` to eliminate sporadic segfaults in Spot/buddy during generator extraction).
- Provide isolated, repeatable tests without relying on external /tmp.

## Running
From the project root:

    python3 kr/testing/test_kr_basic.py          # minimal, normal path, I/O validation, segv-wrapped
    python3 kr/testing/test_kr_reconstruct.py   # clean vs heuristic side-by-side (isolated)
    python3 kr/testing/diag_stability.py

Or as modules (they set up sys.path relative to the file).

Subprocess wrapping per case (in basic and reconstruct) detects segfaults (rc 139/-11) and avoids Spot/Buddy global state accumulation from direct runs.

## Key things tested
- Normal path direct calls to `decompose_aut` + `reconstruct_ltl_1level_buchi` (and `build_infinitely_often_accepting`).
- I/O: produced LTL string, levels, acc count, basic Spot equiv (failing tests OK to focus dev).
- Clean vs heuristic (in reconstruct test).
- 1-level cases (pure K path); multi-level now attempted via generalized reach (up to 2 levels; >2 fallback).
- Segv detection + repeated decomp on problematic formulas (Xa, a, etc.).
- Note: Spot often emits 1/0 for true/false; our code normalizes in some paths; tests accept both.

## Notes on discipline
Test scripts live here (not /tmp). All development artifacts for kr/ should stay under kr/.

See top-level STATUS.md and kr/STATUS.md for overall context and progress on the Boker et al. algebraic translation.
