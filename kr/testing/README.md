# kr/testing/

Internal development and verification scripts for the Krohn-Rhodes (kr/) experimental path.

## Purpose
- Verify the clean vs. heuristic reconstruction after the refactor (moving away from ad-hoc structural pattern matching in `reconstruct_ltl_1level_buchi`).
- Test stability improvements (BDD var precomputation in `bdd_utils.py` to eliminate sporadic segfaults in Spot/buddy during generator extraction, especially with dead-trap completion).
- Provide isolated, repeatable tests without relying on external /tmp.

## Running
From the project root:

    python3 kr/testing/test_kr_reconstruct.py
    python3 kr/testing/diag_stability.py

Or as modules (they set up sys.path relative to the file).

These scripts use subprocess isolation per test case for safety (fresh Python processes avoid accumulating Spot/Buddy global state that can lead to crashes).

## Key things tested
- Both `reconstruct_ltl_1level_buchi` (clean, thin K-operator based) and `_heuristic` (old ad-hoc, kept for comparison).
- `build_infinitely_often_accepting` (the core "G F reach some acc config" using 1-level operators).
- 1-level cases take the pure path; multi-level correctly raises NotImplemented (fall back to heuristic during transition).
- Equivalence checks (where formulas are valid LTL) against original input formulas.
- Repeated decomp on historically problematic formulas (Xa, etc.) to confirm no SEGV.

## Notes on discipline
Test scripts live here (not /tmp). All development artifacts for kr/ should stay under kr/.

See top-level STATUS.md and kr/STATUS.md for overall context and progress on the Boker et al. algebraic translation.
